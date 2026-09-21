# Section 5.2.1 compares four speech-to-text models on 300 recordings
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import DATA_DIRECTORY, RESULTS_DIRECTORY, resolve_data_path

import csv
import json
import re
import statistics
import time
import unicodedata


MANIFEST_DIRECTORY = DATA_DIRECTORY / "manifests"
# 100 recordings each of clear, accented and Singapore accented speech
SPEECH_MANIFESTS = (
    "librispeech_test_clean.csv",
    "mnsc_asr_part1_test.csv",
    "voxpopuli_en_accented.csv",
)
PREDICTIONS_PATH = RESULTS_DIRECTORY / "speech_model_predictions.csv"
SUMMARY_PATH = RESULTS_DIRECTORY / "speech_model_summary.json"

# The four speech-to-text models that were compared
MODELS = [
    ("Whisper", "Whisper Tiny", "openai/whisper-tiny",
     {"language": "en", "task": "transcribe"}),
    ("Whisper", "Whisper Base", "openai/whisper-base",
     {"language": "en", "task": "transcribe"}),
    ("Wav2Vec2", "Wav2Vec2 Base 960h", "facebook/wav2vec2-base-960h", None),
    ("SpeechT5", "SpeechT5 ASR", "microsoft/speecht5_asr",
     {"max_length": 256}),
]

PREDICTION_FIELDS = [
    "model_name",
    "checkpoint",
    "dataset",
    "sample_id",
    "audio_path",
    "reference",
    "prediction",
    "inference_seconds",
    "reference_words",
    "word_errors",
]


# Lowercase and remove punctuation so formatting is not counted as a mistake
def normalise_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.lower().replace("’", "'").replace("'", "")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Count the words the model got wrong against the real transcript
def count_word_errors(reference: str, prediction: str) -> tuple[int, int]:
    from jiwer import process_words

    clean_reference = normalise_text(reference)
    clean_prediction = normalise_text(prediction)
    result = process_words(clean_reference, clean_prediction)

    return (
        result.substitutions + result.deletions + result.insertions,
        len(clean_reference.split()),
    )


def read_manifests() -> list[dict]:
    samples = []

    for name in SPEECH_MANIFESTS:
        with (MANIFEST_DIRECTORY / name).open(
            encoding="utf-8-sig", newline=""
        ) as handle:
            samples.extend(csv.DictReader(handle))

    return samples


def transcribe(speech_model, audio, model_options) -> str:
    options = {}

    if model_options:
        options["generate_kwargs"] = model_options

        # Whisper needs timestamps to read recordings longer than thirty seconds
        if model_options.get("task") == "transcribe" and len(audio) > 30 * 16000:
            options["return_timestamps"] = True

    result = speech_model({"raw": audio, "sampling_rate": 16000}, **options)

    if isinstance(result, dict):
        return (result.get("text") or "").strip()

    return str(result).strip()


def run_the_models(samples: list[dict]) -> list[dict]:
    from transformers import pipeline

    from backend.app.models.speech_to_text import SpeechToTextModel

    rows = []

    for family, name, checkpoint, model_options in MODELS:
        print(f"{name} ...", flush=True)
        speech_model = pipeline(
            "automatic-speech-recognition", model=checkpoint
        )

        # One practice run first so loading the model is not counted in the time
        transcribe(
            speech_model,
            SpeechToTextModel.read_audio(str(resolve_data_path(samples[0]["audio_path"]))),
            model_options,
        )

        for sample in samples:
            audio = SpeechToTextModel.read_audio(
                str(resolve_data_path(sample["audio_path"]))
            )

            started = time.perf_counter()
            prediction = transcribe(speech_model, audio, model_options)
            seconds = time.perf_counter() - started

            errors, words = count_word_errors(sample["reference"], prediction)

            rows.append({
                "model_name": name,
                "checkpoint": checkpoint,
                "dataset": sample["dataset"],
                "sample_id": sample["sample_id"],
                "audio_path": sample["audio_path"],
                "reference": sample["reference"],
                "prediction": prediction,
                "inference_seconds": round(seconds, 6),
                "reference_words": words,
                "word_errors": errors,
            })

        del speech_model

    with PREDICTIONS_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return rows


# Rebuild the results from the saved predictions without loading any models
def read_saved_predictions() -> list[dict]:
    with PREDICTIONS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        row["inference_seconds"] = float(row["inference_seconds"])
        row["reference_words"] = int(row["reference_words"])
        row["word_errors"] = int(row["word_errors"])

    return rows


# The word error rate is taken over every word and the time is the median
def summarise_recordings(rows: list[dict]) -> dict:
    errors = sum(row["word_errors"] for row in rows)
    words = sum(row["reference_words"] for row in rows)

    return {
        "recordings": len(rows),
        "wer_percent": round(errors / words * 100, 2),
        "median_inference_seconds": round(
            statistics.median(row["inference_seconds"] for row in rows), 4
        ),
    }


def main() -> None:
    if "--from-saved-predictions" in sys.argv:
        print("Rebuilding from saved predictions.")
        rows = read_saved_predictions()
    else:
        rows = run_the_models(read_manifests())

    datasets = sorted({row["dataset"] for row in rows})
    models = []

    for family, name, checkpoint, _ in MODELS:
        model_rows = [row for row in rows if row["checkpoint"] == checkpoint]

        models.append({
            "family": family,
            "model_name": name,
            "checkpoint": checkpoint,
            "overall": summarise_recordings(model_rows),
            "by_dataset": {
                dataset: summarise_recordings(
                    [row for row in model_rows if row["dataset"] == dataset]
                )
                for dataset in datasets
            },
        })

    # The lowest word error rate comes first
    models.sort(key=lambda model: model["overall"]["wer_percent"])

    print()
    print(f"  {'model':<22}" + "".join(f"{dataset[:14]:>16}" for dataset in datasets)
          + f"{'overall':>10}{'median s':>10}")

    for model in models:
        print(
            f"  {model['model_name']:<22}"
            + "".join(
                f"{model['by_dataset'][dataset]['wer_percent']:>15.2f}%"
                for dataset in datasets
            )
            + f"{model['overall']['wer_percent']:>9.2f}%"
            + f"{model['overall']['median_inference_seconds']:>9.2f}s"
        )

    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "evaluation": "AI.FIT speech-to-text model comparison",
                "datasets": datasets,
                "models": models,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Saved - {SUMMARY_PATH}")


if __name__ == "__main__":
    main()

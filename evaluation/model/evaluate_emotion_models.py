# Section 5.2.2 compares six natural language inference models on 300 labelled sentences
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import DATA_DIRECTORY, RESULTS_DIRECTORY

import csv
import json
import statistics
import time
from collections import Counter

from backend.app.models.emotional_signal import (
    SHOWN_WORD_TO_SIGNAL,
    EMOTIONAL_SIGNALS,
    SIGNAL_WORDS_SHOWN_TO_MODEL,
)


SENTENCES_PATH = DATA_DIRECTORY / "emotion" / "emotion_evaluation_examples.csv"
PREDICTIONS_PATH = RESULTS_DIRECTORY / "emotion_model_predictions.csv"
SUMMARY_PATH = RESULTS_DIRECTORY / "emotion_model_summary.json"

# High risk recall is the main measure because a dropout application should not miss high risk users
HIGH_RISK_SIGNALS = ("burnout", "low motivation")

# Every model is shown the same label wording the app uses
SIGNAL_WORDS_IN_LABEL_ORDER = [SIGNAL_WORDS_SHOWN_TO_MODEL[label] for label in EMOTIONAL_SIGNALS]

HYPOTHESIS_TEMPLATE = "This person is feeling {}."

# The six natural language inference models that were compared
MODELS = [
    ("BART", "BART Large MNLI", "facebook/bart-large-mnli"),
    ("RoBERTa", "RoBERTa Large MNLI", "FacebookAI/roberta-large-mnli"),
    (
        "DeBERTa",
        "DeBERTa V3 Base MNLI FEVER ANLI",
        "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
    ),
    (
        "DeBERTa",
        "DeBERTa V3 Large Zero-shot V2",
        "MoritzLaurer/deberta-v3-large-zeroshot-v2.0",
    ),
    (
        "DeBERTa",
        "DeBERTa V3 Base Zero-shot V2",
        "MoritzLaurer/deberta-v3-base-zeroshot-v2.0",
    ),
    (
        "DeBERTa",
        "DeBERTa V3 Large MNLI FEVER ANLI Ling WANLI",
        "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
    ),
]

PREDICTION_FIELDS = [
    "model_name",
    "checkpoint",
    "application_model",
    "example_id",
    "context",
    "text",
    "reference_label",
    "predicted_label",
    "scores_json",
    "inference_seconds",
]


def read_dataset() -> list[dict]:
    with SENTENCES_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    counts = Counter(row["reference_label"] for row in rows)

    # The sentences must be balanced with 60 for each of the five signals
    if len(rows) != 300 or any(counts[label] != 60 for label in EMOTIONAL_SIGNALS):
        raise ValueError(
            "The emotion dataset should have 300 sentences with 60 per label."
        )

    return rows


def detect_signal(classifier, text: str) -> dict:
    result = classifier(
        text,
        candidate_labels=SIGNAL_WORDS_IN_LABEL_ORDER,
        hypothesis_template=HYPOTHESIS_TEMPLATE,
        multi_label=False,
    )

    labels = [SHOWN_WORD_TO_SIGNAL[shown] for shown in result["labels"]]

    return {
        "predicted_label": labels[0],
        "scores": dict(zip(labels, map(float, result["scores"]))),
    }


def run_the_models(sentences: list[dict]) -> list[dict]:
    from backend.app.config import settings
    from transformers import pipeline

    rows = []

    for family, name, checkpoint in MODELS:
        print(f"{name} ...", flush=True)
        classifier = pipeline("zero-shot-classification", model=checkpoint)

        # One practice run first so loading the model is not counted in the time
        detect_signal(classifier, sentences[0]["text"])

        for sentence in sentences:
            started = time.perf_counter()
            result = detect_signal(classifier, sentence["text"])
            seconds = time.perf_counter() - started

            rows.append({
                "model_name": name,
                "checkpoint": checkpoint,
                "application_model": checkpoint == settings.emotion_model,
                "example_id": sentence["example_id"],
                "context": sentence["context"],
                "text": sentence["text"],
                "reference_label": sentence["reference_label"],
                "predicted_label": result["predicted_label"],
                "scores_json": json.dumps(result["scores"]),
                "inference_seconds": round(seconds, 6),
            })

        del classifier

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
        row["application_model"] = row["application_model"] == "True"
        row["inference_seconds"] = float(row["inference_seconds"])

    return rows


# Work out the recall for each signal and the mean time for one model
def summarise_model(family, name, checkpoint, rows) -> dict:
    per_label = {}

    for label in EMOTIONAL_SIGNALS:
        written_for_it = [row for row in rows if row["reference_label"] == label]
        right = sum(row["predicted_label"] == label for row in written_for_it)

        per_label[label] = {
            "true_positive": right,
            "total": len(written_for_it),
            "recall_percent": round(right / len(written_for_it) * 100, 2),
        }

    high_risk_found = sum(per_label[label]["true_positive"] for label in HIGH_RISK_SIGNALS)
    high_risk_total = sum(per_label[label]["total"] for label in HIGH_RISK_SIGNALS)
    seconds = [row["inference_seconds"] for row in rows]

    return {
        "family": family,
        "model_name": name,
        "checkpoint": checkpoint,
        "application_model": rows[0]["application_model"],
        "overall": {
            "sentences": len(rows),
            "high_risk_found": high_risk_found,
            "high_risk_recall_percent": round(
                high_risk_found / high_risk_total * 100, 2
            ),
            "mean_inference_seconds": round(statistics.mean(seconds), 4),
            "per_label": per_label,
        },
    }


def main() -> None:
    sentences = read_dataset()

    if "--from-saved-predictions" in sys.argv:
        print("Rebuilding from saved predictions.")
        rows = read_saved_predictions()
    else:
        rows = run_the_models(sentences)

    models = [
        summarise_model(
            family, name, checkpoint,
            [row for row in rows if row["checkpoint"] == checkpoint],
        )
        for family, name, checkpoint in MODELS
    ]

    # The highest high risk recall comes first
    models.sort(key=lambda model: -model["overall"]["high_risk_recall_percent"])

    print()
    print(f"  {'model':<46}{'high-risk recall':>18}{'seconds':>10}")

    for model in models:
        overall = model["overall"]
        marker = "  (in the app)" if model["application_model"] else ""
        print(
            f"  {model['model_name']:<46}"
            f"{overall['high_risk_found']:>6}/120 "
            f"{overall['high_risk_recall_percent']:>6.2f}%"
            f"{overall['mean_inference_seconds']:>9.2f}s{marker}"
        )

    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "evaluation": "AI.FIT emotion model comparison",
                "labels_shown_to_the_model": SIGNAL_WORDS_SHOWN_TO_MODEL,
                "hypothesis_template": HYPOTHESIS_TEMPLATE,
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

# Section 5.3.1 compares eight emotion label wordings with the selected DeBERTa model
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import DATA_DIRECTORY, RESULTS_DIRECTORY

import csv
import json
import random

from backend.app.config import settings

SEED = 42

# 20 sentences for each of the five labels so the data stays balanced and accuracy can be used
SENTENCES_PER_SIGNAL = 20

EMOTIONAL_SIGNALS = [
    "burnout",
    "low motivation",
    "fatigue",
    "high motivation",
    "neutral",
]

HYPOTHESIS_TEMPLATE = "This person is feeling {}."

# Burnout is reworded first and then each of the others on top of it
LABEL_WORDING_COMBINATIONS = {
    "A. plain names from the literature review": {
        "burnout": "burnout",
        "low motivation": "low motivation",
        "fatigue": "fatigue",
        "high motivation": "high motivation",
        "neutral": "neutral",
    },
    "B. burnout only": {
        "burnout": "burnt out",
        "low motivation": "low motivation",
        "fatigue": "fatigue",
        "high motivation": "high motivation",
        "neutral": "neutral",
    },
    "C. burnout, then low motivation": {
        "burnout": "burnt out",
        "low motivation": "unmotivated",
        "fatigue": "fatigue",
        "high motivation": "high motivation",
        "neutral": "neutral",
    },
    # Combination D gave the best trade-off and is the one the app uses
    "D. burnout, low motivation, then fatigue": {
        "burnout": "burnt out",
        "low motivation": "unmotivated",
        "fatigue": "physically tired",
        "high motivation": "high motivation",
        "neutral": "neutral",
    },
    "E. then high motivation as motivated": {
        "burnout": "burnt out",
        "low motivation": "unmotivated",
        "fatigue": "physically tired",
        "high motivation": "motivated",
        "neutral": "neutral",
    },
    "F. burnout, low motivation as less motivated": {
        "burnout": "burnt out",
        "low motivation": "less motivated",
        "fatigue": "fatigue",
        "high motivation": "high motivation",
        "neutral": "neutral",
    },
    "G. burnout, fatigue as plain tired": {
        "burnout": "burnt out",
        "low motivation": "low motivation",
        "fatigue": "tired",
        "high motivation": "high motivation",
        "neutral": "neutral",
    },
    "H. the alternative set, less motivated and tired": {
        "burnout": "burnt out",
        "low motivation": "less motivated",
        "fatigue": "tired",
        "high motivation": "motivated",
        "neutral": "neutral",
    },
}

SENTENCES_PATH = DATA_DIRECTORY / "emotion" / "emotion_evaluation_examples.csv"
SUMMARY_PATH = RESULTS_DIRECTORY / "label_wording.json"


# Pick the same random sentences every time using a fixed seed
def pick_sentences() -> list[dict]:
    with SENTENCES_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    generator = random.Random(SEED)
    chosen = []

    for label in EMOTIONAL_SIGNALS:
        of_this = [row for row in rows if row["reference_label"] == label]
        generator.shuffle(of_this)
        chosen.extend(of_this[:SENTENCES_PER_SIGNAL])

    return chosen


def main() -> None:
    from transformers import pipeline

    samples = pick_sentences()
    texts = [sample["text"] for sample in samples]
    truth = [sample["reference_label"] for sample in samples]

    print(f"{len(samples)} sentences, {SENTENCES_PER_SIGNAL} of each label")
    print(f"Model - {settings.emotion_model}")
    print()

    classifier = pipeline(
        "zero-shot-classification",
        model=settings.emotion_model,
    )

    results = {}

    for name, labels in LABEL_WORDING_COMBINATIONS.items():
        shown = [labels[label] for label in EMOTIONAL_SIGNALS]
        # Turn the reworded labels back into the original labels to mark them
        back = {labels[label]: label for label in EMOTIONAL_SIGNALS}

        outputs = classifier(
            texts,
            candidate_labels=shown,
            hypothesis_template=HYPOTHESIS_TEMPLATE,
            multi_label=False,
        )

        predicted = [back[output["labels"][0]] for output in outputs]
        correct = sum(1 for predicted_label, true_label in zip(predicted, truth) if predicted_label == true_label)

        per_label = {}

        # Work out the recall for each signal
        for label in EMOTIONAL_SIGNALS:
            total = sum(1 for true_label in truth if true_label == label)
            right = sum(
                1 for predicted_label, true_label in zip(predicted, truth)
                if true_label == label and predicted_label == label
            )
            per_label[label] = {
                "correct": right,
                "total": total,
                "recall_percent": round(100 * right / total, 1),
            }

        results[name] = {
            "labels_shown_to_the_model": labels,
            "accuracy_percent": round(100 * correct / len(samples), 1),
            "per_label_recall": per_label,
        }

        print(f"{name}")
        print(f"   accuracy {results[name]['accuracy_percent']}%")

        for label in EMOTIONAL_SIGNALS:
            entry = per_label[label]
            print(f"     {label:<16} "
                  f"{entry['recall_percent']:>5.1f}%  "
                  f"({entry['correct']}/{entry['total']})")

        print()

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "evaluation": "Label wordings, one change at a time",
                "chosen": "D",
                "model": settings.emotion_model,
                "sentences_per_label": SENTENCES_PER_SIGNAL,
                "sentences": len(samples),
                "seed": SEED,
                "template": HYPOTHESIS_TEMPLATE,
                "wordings": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Written to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()

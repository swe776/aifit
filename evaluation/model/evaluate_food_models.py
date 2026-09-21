# Section 5.2.3 checks how often seven food models can identify a food on 184 SNAPMe photographs
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import DATA_DIRECTORY, RESULTS_DIRECTORY

import csv
import json
import time
from collections import defaultdict

from food_text import find_shared_food_groups


SNAPME_MEALS_PATH = DATA_DIRECTORY / "snapme_meals.csv"

SUMMARY_PATH = RESULTS_DIRECTORY / "food_recognition.json"
PREDICTIONS_PATH = RESULTS_DIRECTORY / "food_recognition.csv"

# Three dish classifiers, two food group classifiers and two caption models
FOOD_MODELS = [
    ("Food-101 SigLIP2 93M", "prithivMLmods/Food-101-93M", "classifier"),
    ("Swin Food-101", "aspis/swin-finetuned-food101", "classifier"),
    ("ViT Food-101", "nateraw/food", "classifier"),
    (
        "Kaludi Food Categories 12",
        "Kaludi/food-category-classification-v2.0",
        "classifier",
    ),
    (
        "Kaludi Food Categories 11",
        "Kaludi/food-category-classification",
        "classifier",
    ),
    (
        "BLIP Large",
        "Salesforce/blip-image-captioning-large",
        "caption",
    ),
    (
        "BLIP Base",
        "Salesforce/blip-image-captioning-base",
        "caption",
    ),
]


# The food SNAPMe recorded for each meal is the answer each reading is checked against
def read_meal_descriptions() -> dict[str, str]:
    with SNAPME_MEALS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return {
            meal["filename"]: meal["food_description"]
            for meal in csv.DictReader(handle)
        }


# A model recognises a meal when its reading shares a food group with the meal
def make_reading_row(name, checkpoint, filename, reading, true_food_groups) -> dict:
    return {
        "configuration": name,
        "checkpoint": checkpoint,
        "filename": filename,
        "reading": reading,
        "recognised": bool(find_shared_food_groups(reading) & true_food_groups),
    }


# Run every model on every photograph and time how long each one takes
def read_photos_with_models(described: dict[str, str]):
    from PIL import Image
    from transformers import pipeline

    from backend.app.models.meal_photo import allow_heic_photos
    from snapme_sampling import read_snapme_sample

    allow_heic_photos()

    loaded = []

    for sample in read_snapme_sample():
        with Image.open(sample["image_path"]) as opened:
            loaded.append({
                "filename": sample["filename"],
                "picture": opened.convert("RGB"),
                "true_food_groups": find_shared_food_groups(described[sample["filename"]]),
            })

    print(f"{len(loaded)} photographs loaded.")
    print()

    rows = []
    seconds_per_photograph = {}

    for name, checkpoint, kind in FOOD_MODELS:
        print(f"{name} ...", end=" ", flush=True)
        started = time.perf_counter()

        # Classifiers name one class and caption models write a sentence
        if kind == "classifier":
            model = pipeline(
                "image-classification", model=checkpoint, top_k=1
            )
        else:
            model = pipeline("image-text-to-text", model=checkpoint)

        for item in loaded:
            if kind == "classifier":
                reading = model(item["picture"])[0]["label"].replace("_", " ")
            else:
                output = model(
                    item["picture"],
                    text="A photo of",
                    max_new_tokens=40,
                )
                reading = (
                    (output[0].get("generated_text") or "").strip()
                    if output else ""
                )

            rows.append(make_reading_row(
                name, checkpoint, item["filename"], reading,
                item["true_food_groups"],
            ))

        seconds = time.perf_counter() - started
        seconds_per_photograph[name] = round(seconds / len(loaded), 4)
        print(f"{seconds / 60:.1f} min")

        del model

    return rows, seconds_per_photograph


# Mark the saved readings again without loading any models
def read_saved_readings(described: dict[str, str]):
    with PREDICTIONS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        saved = list(csv.DictReader(handle))

    rows = [
        make_reading_row(
            row["configuration"], row["checkpoint"], row["filename"],
            row["reading"], find_shared_food_groups(described[row["filename"]]),
        )
        for row in saved
    ]

    previous = json.loads(SUMMARY_PATH.read_text(encoding="utf-8-sig"))
    seconds_per_photograph = {
        entry["configuration"]: entry["seconds_per_photograph"]
        for entry in previous["configurations"]
    }

    return rows, seconds_per_photograph


def main() -> None:
    described = read_meal_descriptions()

    print()
    print("CAN EACH FOOD MODEL NAME A FOOD THAT IS ON THE PLATE?")
    print("=" * 74)

    if "--from-saved-readings" in sys.argv:
        print("Rescoring the saved readings.")
        rows, seconds_per_photograph = read_saved_readings(described)
    else:
        rows, seconds_per_photograph = read_photos_with_models(described)

    by_configuration = defaultdict(list)

    for row in rows:
        by_configuration[row["configuration"]].append(row)

    summaries = []

    for name, checkpoint, kind in FOOD_MODELS:
        group = by_configuration[name]
        found = sum(row["recognised"] for row in group)

        summaries.append({
            "configuration": name,
            "checkpoint": checkpoint,
            "kind": kind,
            "photographs": len(group),
            "recognised": found,
            "recognised_percent": round(found / len(group) * 100, 2),
            "seconds_per_photograph": seconds_per_photograph[name],
        })

    # The model that recognised the most food comes first
    summaries.sort(key=lambda summary: -summary["recognised_percent"])

    print()
    print(f"{'configuration':<30}{'recognised':>16}{'seconds':>10}")

    for summary in summaries:
        print(
            f"{summary['configuration']:<30}"
            f"{summary['recognised']:>4}/{summary['photographs']:<4}"
            f"{summary['recognised_percent']:>7.2f}%"
            f"{summary['seconds_per_photograph']:>9.2f}s"
        )

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "evaluation": (
                    "Can each food model name a food that is on the plate?"
                ),
                "configurations": summaries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with PREDICTIONS_PATH.open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"Saved - {SUMMARY_PATH}")
    print(f"Saved - {PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()

# Section 5.3.2 checks if showing three readings is better than one
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import DATA_DIRECTORY, RESULTS_DIRECTORY

import csv
import json
from collections import defaultdict

from backend.app.config import settings
from backend.app.logic.meal_band_rules import (
    calc_band_from_food_group,
    calc_band_from_reading,
)

FOOD_READINGS_PATH = RESULTS_DIRECTORY / "food_recognition.csv"
SNAPME_MEALS_PATH = DATA_DIRECTORY / "snapme_meals.csv"
SUMMARY_PATH = RESULTS_DIRECTORY / "three_readings.json"

# The three readings the app shows and how each one becomes a band
THREE_READINGS = (
    ("Food-101 dish", settings.dish_model, calc_band_from_reading),
    ("Food-group classifier", settings.food_group_model, calc_band_from_food_group),
    ("BLIP caption", settings.caption_model, calc_band_from_reading),
)


def percent(count: int, total: int) -> float:
    return round(count / total * 100, 2) if total else 0.0


def main() -> None:
    with SNAPME_MEALS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        true_band = {
            meal["filename"]: meal["reference_nutrition_category"]
            for meal in csv.DictReader(handle)
        }

    if not FOOD_READINGS_PATH.exists():
        raise FileNotFoundError(
            f"{FOOD_READINGS_PATH} is missing. Run evaluate_food_models.py first."
        )

    by_photo: dict[str, dict[str, dict]] = defaultdict(dict)

    with FOOD_READINGS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            by_photo[row["filename"]][row["checkpoint"]] = row

    photographs = sorted(by_photo)
    total = len(photographs)

    each_reading = {
        name: {"food_recognised": 0, "correct_band": 0}
        for name, _, _ in THREE_READINGS
    }
    any_recognised = 0
    any_band_right = 0

    # For each photograph check if at least one reading recognised the food and gave the right band
    for filename in photographs:
        recognised_here = False
        band_right_here = False

        for name, checkpoint, to_band in THREE_READINGS:
            row = by_photo[filename][checkpoint]
            recognised = row["recognised"] == "True"
            band_right = to_band(row["reading"]) == true_band[filename]

            each_reading[name]["food_recognised"] += recognised
            each_reading[name]["correct_band"] += band_right
            recognised_here |= recognised
            band_right_here |= band_right

        # A photograph counts when any one of the three readings got it right
        any_recognised += recognised_here
        any_band_right += band_right_here

    for result in each_reading.values():
        result["food_recognised_percent"] = percent(
            result["food_recognised"], total
        )
        result["correct_band_percent"] = percent(
            result["correct_band"], total
        )

    print()
    print("DOES SHOWING THREE READINGS HELP?")
    print("=" * 66)
    print(f"{total} SNAPMe photographs.")
    print()
    print(f"  {'reading':<34}{'recognised':>14}{'correct band':>16}")

    for name, result in each_reading.items():
        print(
            f"  {name:<34}"
            f"{result['food_recognised']:>4}/{total} "
            f"{result['food_recognised_percent']:>6.2f}%"
            f"{result['correct_band']:>6}/{total} "
            f"{result['correct_band_percent']:>6.2f}%"
        )

    print(
        f"  {'At least one of the three':<34}"
        f"{any_recognised:>4}/{total} {percent(any_recognised, total):>6.2f}%"
        f"{any_band_right:>6}/{total} {percent(any_band_right, total):>6.2f}%"
    )

    summary = {
        "evaluation": "Does showing three food readings do better than one?",
        "photographs": total,
        "each_reading": each_reading,
        "at_least_one_model_recognised_the_food": {
            "count": any_recognised,
            "percent": percent(any_recognised, total),
        },
        "at_least_one_reading_gave_the_right_band": {
            "count": any_band_right,
            "percent": percent(any_band_right, total),
        },
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print(f"Saved - {SUMMARY_PATH}")


if __name__ == "__main__":
    main()

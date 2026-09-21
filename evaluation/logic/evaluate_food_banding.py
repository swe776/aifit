# Section 5.2.3 checks how well the three selected models assign the nutrition band
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

SNAPME_MEALS_PATH = DATA_DIRECTORY / "snapme_meals.csv"
FOOD_READINGS_PATH = RESULTS_DIRECTORY / "food_recognition.csv"
SUMMARY_PATH = RESULTS_DIRECTORY / "food_banding.json"

MEAL_BANDS = ("balanced", "mixed", "poor")

# Each reading is turned into a band exactly the way the app does it
SELECTED_MODELS = {
    settings.dish_model: calc_band_from_reading,
    settings.food_group_model: calc_band_from_food_group,
    settings.caption_model: calc_band_from_reading,
}


# Macro F1 gives each band equal weight so the most common band does not skew the result
def calc_macro_f1(pairs: list[tuple[str, str]]) -> dict:
    per_band = {}
    f1s = []

    for band in MEAL_BANDS:
        total = sum(true == band for _, true in pairs)
        times_said = sum(said == band for said, _ in pairs)
        got = sum(said == true == band for said, true in pairs)

        recall = got / total if total else 0.0
        precision = got / times_said if times_said else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )

        per_band[band] = {
            "correct": got,
            "total": total,
            "said": times_said,
            "f1_percent": round(f1 * 100, 2),
        }

        f1s.append(f1)

    return {
        "photographs": len(pairs),
        "macro_f1_percent": round(sum(f1s) / len(f1s) * 100, 2),
        "per_band": per_band,
    }


def main() -> None:
    with SNAPME_MEALS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        # The reference band comes from the nutrients SNAPMe measured and the HPB guidance
        truth = {
            meal["filename"]: meal["reference_nutrition_category"]
            for meal in csv.DictReader(handle)
            if meal["food_description"].strip()
        }

    if not FOOD_READINGS_PATH.exists():
        raise FileNotFoundError(
            f"{FOOD_READINGS_PATH} is missing. Run evaluate_food_models.py first."
        )

    with FOOD_READINGS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        readings = list(csv.DictReader(handle))

    by_model: dict[str, list[tuple[str, str]]] = defaultdict(list)
    photographed: set[str] = set()

    for row in readings:
        true_band = truth.get(row["filename"])
        calc_band = SELECTED_MODELS.get(row["checkpoint"])

        # Only the three selected models are marked
        if not true_band or calc_band is None:
            continue

        photographed.add(row["filename"])
        # A reading the app shows as not sure is counted as wrong
        by_model[row["configuration"]].append(
            (calc_band(row["reading"]) or "not sure", true_band)
        )

    if not by_model:
        raise ValueError(
            f"{FOOD_READINGS_PATH} has no SNAPMe meals in it. "
            "Run evaluate_food_models.py again."
        )

    models = {name: calc_macro_f1(pairs) for name, pairs in by_model.items()}

    # The model with the highest macro F1 comes first
    ranked = sorted(
        models.items(), key=lambda pair: -pair[1]["macro_f1_percent"]
    )

    print()
    print("CAN A FOOD MODEL PLACE A PHOTOGRAPHED MEAL INTO A BAND?")
    print("=" * 74)
    print(f"{len(photographed)} SNAPMe photographs (the three selected models banded the way the app does it).")
    print()
    print(
        f"  {'model':<30}{'macro F1':>10}"
        f"{'balanced':>11}{'mixed':>9}{'poor':>9}"
    )
    print("  " + "-" * 69)

    for name, result in ranked:
        bands = result["per_band"]
        print(
            f"  {name:<30}{result['macro_f1_percent']:>9.2f}%"
            f"{bands['balanced']['f1_percent']:>10.2f}%"
            f"{bands['mixed']['f1_percent']:>8.2f}%"
            f"{bands['poor']['f1_percent']:>8.2f}%"
        )

    best_name = ranked[0][0]

    print()
    print(f"  Best model - {best_name}")

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "evaluation": "Can a food model place a photographed meal into a band?",
                "photographs": len(photographed),
                "each_model": models,
                "best_model": best_name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Saved - {SUMMARY_PATH}")


if __name__ == "__main__":
    main()

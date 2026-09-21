# Section 5.3.3 tests every balanced and poor combination on all SNAPMe meals
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import DATA_DIRECTORY, RESULTS_DIRECTORY

import csv
import json
from collections import Counter

from backend.app.logic.meal_band_rules import (
    POSITIVE_NUTRITION_GROUPS,
    POOR_NUTRITION_GROUPS,
    find_foods_and_groups,
)


SNAPME_MEALS_PATH = DATA_DIRECTORY / "snapme_meals.csv"

# Build one banding rule from how many balanced and poor groups it needs
def make_band_rule(balanced_needed: int, poor_needed: int, lone_poor: bool):
    def rule(meal_groups: set) -> str:
        balanced = len(meal_groups & POSITIVE_NUTRITION_GROUPS)
        poor = len(meal_groups & POOR_NUTRITION_GROUPS)

        if balanced >= balanced_needed and poor == 0:
            return "balanced"

        # Some rules also count a meal as poor when it has one poor group and nothing balanced
        if poor >= poor_needed or (lone_poor and poor >= 1 and balanced == 0):
            return "poor"

        return "mixed"

    return rule


ALL_BAND_RULES = {}

# Together these make the 20 combinations that were tested
for _balanced in (1, 2, 3, 4):
    for _poor in (1, 2, 3):
        ALL_BAND_RULES[f"balanced {_balanced}, poor {_poor}"] = make_band_rule(
            _balanced, _poor, True
        )

        if _poor > 1:
            ALL_BAND_RULES[
                f"balanced {_balanced}, poor {_poor}, no lone poor"
            ] = make_band_rule(_balanced, _poor, False)

# The app keeps B3/P2 because users found the best combination too strict
APP_BAND_RULE = "balanced 3, poor 2"


# Macro F1 gives balanced, mixed and poor equal weight
def calc_macro_f1(rows: list, rule) -> dict:
    produced = Counter(rule(row["meal_groups"]) for row in rows)
    per_band = {}

    for band in ("balanced", "mixed", "poor"):
        of_this = [row for row in rows if row["truth"] == band]
        right = sum(1 for row in of_this if rule(row["meal_groups"]) == band)
        said = produced[band]

        recall = right / len(of_this) if of_this else 0.0
        precision = right / said if said else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )

        per_band[band] = {
            "correct": right,
            "total": len(of_this),
            "said": said,
            "f1_percent": round(100 * f1, 2),
        }

    macro_f1 = round(
        sum(band_result["f1_percent"] for band_result in per_band.values()) / 3, 2
    )

    return {
        "scored": len(rows),
        "macro_f1_percent": macro_f1,
        "per_band": per_band,
        "what_it_says": dict(produced),
    }


def main() -> None:
    with SNAPME_MEALS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        meals = list(csv.DictReader(handle))

    rows = []
    without_a_description = 0

    # Every meal can be tested because no model is used and only the recorded food is read
    for meal in meals:
        description = meal["food_description"].strip()

        # Skip a meal that has no food names
        if not description:
            without_a_description += 1
            continue

        rows.append(
            {
                "truth": meal["reference_nutrition_category"],
                "meal_groups": find_foods_and_groups(description)[1],
            }
        )

    print()
    print("WHICH BAND RULE PLACES A MEAL IN THE RIGHT BAND BEST")
    print("=" * 74)
    print(f"{len(rows)} SNAPMe meals.")

    if without_a_description:
        print(f"{without_a_description} carried no food names.")

    print()

    results = {name: calc_macro_f1(rows, rule) for name, rule in ALL_BAND_RULES.items()}

    # The combination with the highest macro F1 comes first
    ranked = sorted(
        results.items(),
        key=lambda pair: -pair[1]["macro_f1_percent"],
    )

    print(f"  {'macro F1':>9}   rule")

    for name, result in ranked:
        print(f"  {result['macro_f1_percent']:>8.2f}%   {name}")

    best_name = ranked[0][0]

    print()
    print(f"Best on macro F1 - {best_name}")

    # Show where the app's rule came in the ranking
    if APP_BAND_RULE != best_name:
        place = [name for name, _ in ranked].index(APP_BAND_RULE) + 1
        print(
            f"In the application - {APP_BAND_RULE}, "
            f"{results[APP_BAND_RULE]['macro_f1_percent']:.2f}% macro F1 "
            f"(place {place} of {len(ranked)})"
        )
        print()


    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    (RESULTS_DIRECTORY / "band_rules.json").write_text(
        json.dumps(
            {
                "evaluation": "Nutrient group combinations",
                "meals": len(rows),
                "results": results,
                "best": best_name,
                "in_the_application": APP_BAND_RULE,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Written to {RESULTS_DIRECTORY / 'band_rules.json'}")


if __name__ == "__main__":
    main()

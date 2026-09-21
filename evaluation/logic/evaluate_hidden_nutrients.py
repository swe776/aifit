# Section 5.3.4 checks how much of the nutrition band a photograph can or cannot show
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import DATA_DIRECTORY, RESULTS_DIRECTORY

import collections
import csv
import json

from hpb_reference_band import (
    FIBRE_G,
    FRUIT_VEG,
    PROTEIN_G,
    WHOLEGRAIN_OZ,
    calc_reference_band,
)

SNAPME_MEALS_PATH = DATA_DIRECTORY / "snapme_meals.csv"
SUMMARY_PATH = RESULTS_DIRECTORY / "hidden_nutrients.json"


# Work out the reference band again without saturated fat, sodium and added sugar
def band_without_hidden_nutrients(record: dict) -> str:
    positive_checks = [
        float(record["PROT"]) >= PROTEIN_G,
        float(record["FIBE"]) >= FIBRE_G,
        float(record["F_TOTAL"]) + float(record["V_TOTAL"]) >= FRUIT_VEG,
        float(record["G_WHOLE"]) >= WHOLEGRAIN_OZ,
    ]

    # With the poor checks gone a meal can only be balanced or mixed
    if sum(positive_checks) >= 3:
        return "balanced"

    return "mixed"


def main() -> None:
    with SNAPME_MEALS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        meals = list(csv.DictReader(handle))

    moves = collections.Counter()
    changed = 0

    # Count how many meals change band once the hidden nutrients are removed
    for meal in meals:
        real = calc_reference_band(meal)
        without = band_without_hidden_nutrients(meal)
        moves[(real, without)] += 1

        if real != without:
            changed += 1

    print()
    print("HOW MUCH OF THE BAND IS NOT IN THE PHOTOGRAPH?")
    print("=" * 70)
    print(f"{len(meals)} real meals from SNAPMe.")
    print()
    print(
        "Rebuilding the band with saturated fat, sodium and added sugar removed"
    )
    print()
    print(f"  {changed} of {len(meals)} meals change band "
          f"({changed / len(meals) * 100:.1f}%)")
    print()

    for (real, without), count in moves.most_common():
        mark = "" if real == without else "   changes"
        print(f"  {real:<9} -> {without:<9}{count:>6}{mark}")

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(
        json.dumps(
            {
                "evaluation": "How much of the reference band is not in the photograph?",
                "meals": len(meals),
                "meals_that_change_band": changed,
                "meals_that_change_band_percent": round(
                    changed / len(meals) * 100, 2
                ),
                "where_they_move": {
                    f"{real} to {without}": count
                    for (real, without), count in moves.items()
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Saved - {SUMMARY_PATH}")


if __name__ == "__main__":
    main()

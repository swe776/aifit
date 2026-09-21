# Unit tests for the B3/P2 band rule and the Objective 2 rater sheets
from itertools import combinations
import csv
import sys
from pathlib import Path
import pytest

from backend.app.logic.meal_band_rules import POSITIVE_NUTRITION_GROUPS, POOR_NUTRITION_GROUPS, calc_b3p2_band, calc_band_from_food_group
sys.path.insert(0, str(Path(__file__).parents[3] / "evaluation" / "shared"))
from hpb_reference_band import calc_reference_band


# The app rule and the HPB reference band must agree for every group combination
def test_all_group_combinations_agree_with_nutrient_reference():
    positive_groups = sorted(POSITIVE_NUTRITION_GROUPS)
    poor_groups = sorted(POOR_NUTRITION_GROUPS)
    group_nutrient_amounts = {
        "protein": ("PROT", 20), "fibre": ("FIBE", 10),
        "produce": ("V_TOTAL", 2), "wholegrain": ("G_WHOLE", 1),
        "satfat": ("SFAT", 10), "sodium": ("SODI", 700),
        "sugar": ("ADD_SUGARS", 4),
    }
    for num_positive in range(5):
        for num_poor in range(4):
            expected = (
                "balanced" if num_positive >= 3 and num_poor == 0 else
                "poor" if num_poor >= 2 or (num_poor == 1 and num_positive == 0) else
                "mixed"
            )
            for chosen_positive_groups in combinations(positive_groups, num_positive):
                for chosen_poor_groups in combinations(poor_groups, num_poor):
                    meal_groups = set(chosen_positive_groups + chosen_poor_groups)
                    nutrients = dict.fromkeys(
                        ("PROT", "FIBE", "V_TOTAL", "F_TOTAL", "G_WHOLE", "SFAT", "SODI", "ADD_SUGARS"), 0)
                    nutrients["KCAL"] = 500
                    for group in meal_groups:
                        key, value = group_nutrient_amounts[group]
                        nutrients[key] = value
                    assert calc_b3p2_band(meal_groups) == expected
                    assert calc_reference_band(nutrients) == expected


def test_objective2_needs_three_matching_rater_sheets(tmp_path, monkeypatch):
    from evaluation.objectives import evaluate_objective2 as objective2
    monkeypatch.setattr(objective2, "RATER_SHEETS_DIRECTORY", tmp_path)
    case = {"case_id": "B3P2-C01", "reference_transcript": "A journal",
            "food_label": "A meal"}
    row = {"case_id": case["case_id"], "fitness_journal": "A journal",
           "true_meal_description": "A meal", objective2.RATING_COLUMN: "low"}

    def write(name, value):
        with (tmp_path / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=value.keys())
            writer.writeheader()
            writer.writerow(value)

    write("rater_1.csv", row)
    write("rater_2.csv", row)
    write("rater_3.csv", dict(row, true_meal_description="A different meal"))

    with pytest.raises(SystemExit, match="Three completed"):
        objective2.read_rater_labels([case.copy()])

    write("rater_3.csv", row)
    labels = objective2.read_rater_labels([case.copy()])

    assert labels["rater_count"] == 3


def test_broad_produce_classes_do_not_imply_three_positive_groups():
    assert calc_band_from_food_group("Fruit") == "mixed"
    assert calc_band_from_food_group("Vegetable") == "mixed"

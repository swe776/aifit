# Section 5.5.2 tests if voice and meal together classify dropout risk better than voice alone
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import (
    DATA_DIRECTORY,
    EVALUATION_DIRECTORY,
    PROJECT_ROOT,
    RESULTS_DIRECTORY,
)

import csv
import json
from collections import Counter

RATER_SHEETS_DIRECTORY = DATA_DIRECTORY / "rater_sheets"

RISK_LEVELS = ["low", "medium", "high"]

RATING_COLUMN = "risk_label_low_medium_or_high"

RISK_LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2}

# Voice only uses a mixed meal and meal only uses a neutral signal if there is missing input
MISSING_MEAL_BAND = "mixed"
MISSING_EMOTIONAL_SIGNAL = "neutral"


from backend.app.logic.dropout_risk_score import calc_dropout_risk


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def find_case_file(stored_path: str) -> Path:
    cleaned = str(stored_path).replace("\\", "/").strip()
    candidate = PROJECT_ROOT / cleaned

    if candidate.is_file():
        return candidate

    parts = [part for part in Path(cleaned).parts if part not in (".", "")]

    while parts and parts[0] == "evaluation":
        parts = parts[1:]

    return EVALUATION_DIRECTORY.joinpath(*parts)


def calc_accuracy(truth: list[str], predictions: list[str]) -> dict:
    total = len(truth)
    correct = sum(
        1 for true_label, predicted_label in zip(truth, predictions) if true_label == predicted_label
    )

    return {
        "cases": total,
        "correct": correct,
        "accuracy_percent": (
            round(correct / total * 100, 2) if total else 0.0
        ),
    }


# Three raters labelled every case as low, medium or high dropout risk
def read_rater_labels(cases: list[dict]) -> dict:
    sheets = []

    numbers = sorted(
        int(path.stem.split("_")[1])
        for path in RATER_SHEETS_DIRECTORY.glob("rater_*.csv")
        if path.stem.split("_")[1].isdigit()
    )

    for number in numbers:
        path = RATER_SHEETS_DIRECTORY / f"rater_{number}.csv"

        if not path.is_file():
            continue

        sheet_rows = read_csv(path)
        case_by_id = {case["case_id"]: case for case in cases}
        # A sheet is only used when it rates exactly the same 36 cases
        if len(sheet_rows) != len(cases) or {row["case_id"] for row in sheet_rows} != set(case_by_id):
            print(f"Sheet {number} does not match the cases so it is being skipped.")
            continue
        if any(
            row.get("fitness_journal") != case_by_id[row["case_id"]]["reference_transcript"]
            or row.get("true_meal_description") != case_by_id[row["case_id"]]["food_label"]
            for row in sheet_rows
        ):
            print(f"Sheet {number} has different journals or meals so it is being skipped.")
            continue
        ratings = {
            row["case_id"]: row[RATING_COLUMN].strip().lower()
            for row in sheet_rows
        }

        if all(
            ratings.get(case["case_id"]) in RISK_LEVELS
            for case in cases
        ):
            sheets.append({"number": number, "ratings": ratings})
        else:
            filled = sum(
                1 for rating in ratings.values() if rating in RISK_LEVELS
            )
            print(
                f"Sheet {number} is unfinished "
                f"({filled} of {len(cases)}) so it is being skipped."
            )

    if len(sheets) != 3:
        raise SystemExit(
            "Three completed rater sheets are needed for all 36 cases."
        )

    disagreements = []

    for case in cases:
        given = [sheet["ratings"][case["case_id"]] for sheet in sheets]

        # If all three raters agreed that label is used
        if len(set(given)) == 1:
            case["reference_risk_label"] = given[0]
        else:
            counts = Counter(given)
            most = max(counts.values())
            tied = [
                label for label, count in counts.items() if count == most
            ]
            # Else the majority vote is used and a tie keeps the more serious risk label
            chosen = max(tied, key=lambda level: RISK_LEVEL_ORDER[level])

            case["reference_risk_label"] = chosen
            disagreements.append(
                {
                    "case_id": case["case_id"],
                    "ratings": {
                        f"rater_{sheet['number']}": (
                            sheet["ratings"][case["case_id"]]
                        )
                        for sheet in sheets
                    },
                    "agreed_label": chosen,
                    "rule": (
                        "majority vote"
                        if len(tied) == 1
                        else "tied so the more serious label was kept"
                    ),
                }
            )

        for sheet in sheets:
            case[f"rater_{sheet['number']}"] = (
                sheet["ratings"][case["case_id"]]
            )

    return {
        "sheets": sheets,
        "rater_count": len(sheets),
        "disagreements": disagreements,
    }


# Fleiss' kappa measures how much the three raters agreed
def fleiss_kappa(ratings_per_case: list[list[str]]) -> float:
    cases = len(ratings_per_case)
    raters = len(ratings_per_case[0])

    if cases == 0 or raters < 2:
        return None

    total_ratings = cases * raters
    label_share = {
        label: sum(
            row.count(label) for row in ratings_per_case
        ) / total_ratings
        for label in RISK_LEVELS
    }

    agreement = []

    for row in ratings_per_case:
        same_pairs = sum(row.count(label) ** 2 for label in RISK_LEVELS)
        agreement.append(
            (same_pairs - raters) / (raters * (raters - 1))
        )

    observed = sum(agreement) / cases
    expected = sum(share ** 2 for share in label_share.values())

    if expected == 1:
        return 1.0

    return round((observed - expected) / (1 - expected), 3)


# Run the real models on the 12 recordings and the 36 meal photographs (1 rec a day with 3 meals were used)
def run_the_models(cases: list[dict]):
    from backend.app.models.emotional_signal import detect_emotional_signal
    from backend.app.models.meal_photo import read_meal_photo
    from backend.app.models.speech_to_text import transcribe_audio

    audio_results: dict[str, dict] = {}
    image_results: dict[str, dict] = {}

    unique_audio = sorted({case["audio_path"] for case in cases})
    unique_images = sorted({case["image_path"] for case in cases})

    for position, stored in enumerate(unique_audio, start=1):
        transcript = transcribe_audio(str(find_case_file(stored))).strip()
        emotion = detect_emotional_signal(transcript)

        audio_results[stored] = {
            "transcript": transcript,
            "label": emotion["label"],
            "confidence": emotion["confidence"],
            "scores": emotion["scores"],
        }

        print(f"Audio {position} of {len(unique_audio)}")

    for position, stored in enumerate(unique_images, start=1):
        try:
            # No user picks a reading here so the first reading with a band is used
            nutrition = read_meal_photo(str(find_case_file(stored)))
            image_results[stored] = {
                "food_label": nutrition["food_label"],
                "band": nutrition["nutrition_category"],
                "rejected": False,
            }

        except ValueError as error:
            image_results[stored] = {
                "food_label": "",
                "band": "",
                "rejected": True,
                "rejection_reason": str(error),
            }

        print(f"Image {position} of {len(unique_images)}")

    return audio_results, image_results


def main() -> None:
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    cases = read_csv(DATA_DIRECTORY / "objective2_cases.csv")

    if len(cases) != 36:
        raise SystemExit(f"Expected 36 cases but found {len(cases)}.")
    # Each journal is paired with one balanced, one mixed and one poor meal
    if Counter(case["reference_nutrition_category"] for case in cases) != {"balanced": 12, "mixed": 12, "poor": 12}:
        raise SystemExit("Expected 12 cases for each meal band.")

    reference = read_rater_labels(cases)
    rater_count = reference["rater_count"]

    kappa = fleiss_kappa([
        [
            case[f"rater_{sheet['number']}"]
            for sheet in reference["sheets"]
        ]
        for case in cases
    ])

    print(f"Fleiss' kappa across {rater_count} raters - {kappa}")

    audio_results, image_results = run_the_models(cases)

    rows = []

    for case in cases:
        audio = audio_results[case["audio_path"]]
        image = image_results[case["image_path"]]

        predicted_band = image["band"] or MISSING_MEAL_BAND

        # Score every case three ways with voice and meal together then voice only then meal only
        both = calc_dropout_risk(
            audio["label"],
            predicted_band,
            audio["scores"],
        )
        voice_only = calc_dropout_risk(
            audio["label"], MISSING_MEAL_BAND, audio["scores"]
        )
        meal_only = calc_dropout_risk(
            MISSING_EMOTIONAL_SIGNAL, predicted_band
        )

        rows.append(
            {
                "case_id": case["case_id"],
                "journal_id": case["journal_id"],
                "reference_emotion": case["reference_emotion"],
                "reference_nutrition_category": (
                    case["reference_nutrition_category"]
                ),
                "reference_risk_label": case["reference_risk_label"],
                "reference_transcript": case["reference_transcript"],
                "generated_transcript": audio["transcript"],
                "predicted_emotion": audio["label"],
                "emotion_confidence": audio["confidence"],
                "predicted_food": image["food_label"],
                "meal_photo_rejected": image["rejected"],
                "predicted_nutrition_category": predicted_band,
                "predicted_risk_score": both.dropout_risk_score,
                "both_inputs_risk_label": both.dropout_risk_level,
                "voice_only_risk_label": voice_only.dropout_risk_level,
                "meal_only_risk_label": meal_only.dropout_risk_level,
            }
        )

    write_csv(RESULTS_DIRECTORY / "objective2_predictions.csv", rows)

    if reference["disagreements"]:
        write_csv(
            RESULTS_DIRECTORY / "objective2_rater_disagreements.csv",
            reference["disagreements"],
        )

    truth = [row["reference_risk_label"] for row in rows]

    voice_result = calc_accuracy(truth, [row["voice_only_risk_label"] for row in rows])
    both_result = calc_accuracy(truth, [row["both_inputs_risk_label"] for row in rows])
    meal_result = calc_accuracy(truth, [row["meal_only_risk_label"] for row in rows])
    results = (voice_result, both_result, meal_result)

    all_three_tested = all(
        result["cases"] == len(cases) for result in results
    )

    shows_which_is_better = all(
        result["accuracy_percent"] is not None for result in results
    )

    summary = {
        "evaluation": "AI.FIT Objective 2 evaluation",
        "case_count": len(rows),
        "unique_journals": len({row["journal_id"] for row in rows}),
        "rater_count": rater_count,
        "fleiss_kappa": kappa,
        "voice_only": voice_result,
        "both_together": both_result,
        "meal_only": meal_result,
        "three_combinations_tested": all_three_tested,
        "results_show_which_performed_better": shows_which_is_better,
        "objective_met": all_three_tested and shows_which_is_better,
    }

    (RESULTS_DIRECTORY / "objective2_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    def line(name, result):
        return (
            f"  {name:<24}{result['correct']}/{result['cases']}   "
            f"{result['accuracy_percent']}%"
        )

    lines = [
        "AI.FIT OBJECTIVE 2 EVALUATION",
        "=" * 66,
        "Does adding a meal photograph make the prediction better?",
        "",
        f"{len(rows)} cases, from "
        f"{summary['unique_journals']} journals and "
        f"{len(rows)} meal photographs.",
        f"Raters - {rater_count}   Fleiss' kappa - {kappa}",
        "",
        "RESULTS",
        "-" * 66,
        line("Voice entry only", voice_result),
        line("Both together", both_result),
        line("Meal photograph only", meal_result),
        "",
        "IS THE OBJECTIVE MET",
        "-" * 66,
        f"  Three combinations tested                  "
        f"{'MET' if all_three_tested else 'NOT MET'}",
        f"  Results show which performed better        "
        f"{'MET' if shows_which_is_better else 'NOT MET'}",
        "",
        f"Objective met - "
        f"{'YES' if summary['objective_met'] else 'NO'}",
    ]

    print()
    print("\n".join(lines))
    print()
    print(f"Saved - {RESULTS_DIRECTORY / 'objective2_summary.json'}")


if __name__ == "__main__":
    main()

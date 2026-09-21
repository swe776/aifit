# Section 5.4 tests which baseline settings best detect a risk change on seed generated histories
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

from paths import RESULTS_DIRECTORY

import csv
import json
import random

from backend.app.logic import personal_baseline


SEED = 42

SUMMARY_PATH = RESULTS_DIRECTORY / "baseline_settings.json"
TABLE_PATH = RESULTS_DIRECTORY / "baseline_settings.csv"

# Scores stay between the lowest and highest score a real check-in can get
LOWEST_POSSIBLE_SCORE = 2.0
HIGHEST_POSSIBLE_SCORE = 8.5

# The average of 3, 5 and 10 past scores with five thresholds gives 15 combinations
PREV_SCORE_COUNTS_TESTED = [3, 5, 10]
CHANGE_THRESHOLDS_TESTED = [0.5, 1.0, 1.5, 2.0, 2.5]

# 400 increasing, 400 decreasing and 400 stable histories
HISTORIES_PER_TYPE = 400
HISTORY_TYPES = ["increasing", "decreasing", "stable"]

MOST_PREV_SCORES_TESTED = max(PREV_SCORE_COUNTS_TESTED)
HISTORY_LENGTH = MOST_PREV_SCORES_TESTED + 1

# Each history has random variation to represent small changes between check-ins
RANDOM_VARIATION = 0.6
CHANGE_PER_CHECKIN = (0.6, 1.0)

# Each history starts from a different score
STABLE_START_RANGE = (3.5, 7.0)
INCREASING_START_RANGE = (2.5, 4.0)
DECREASING_START_RANGE = (6.5, 8.0)

# The settings the app uses so they can be marked in the results
APP_PREV_SCORES_TAKEN = personal_baseline.PREV_NUM_BASELINE_SCORES_TAKEN
APP_RISK_CHANGE_THRESHOLD = personal_baseline.RISK_CHANGE_THRESHOLD


def keep_score_in_range(score):
    return max(LOWEST_POSSIBLE_SCORE, min(HIGHEST_POSSIBLE_SCORE, score))


# Make one increasing, decreasing or stable history of scores
def generate_history(history_type, num_scores, random_numbers):
    def random_change():
        return random_numbers.gauss(0.0, RANDOM_VARIATION)

    if history_type == "stable":
        usual_score = random_numbers.uniform(*STABLE_START_RANGE)

        return [
            keep_score_in_range(usual_score + random_change())
            for _ in range(num_scores)
        ]

    change = random_numbers.uniform(*CHANGE_PER_CHECKIN)

    if history_type == "increasing":
        start = random_numbers.uniform(*INCREASING_START_RANGE)

        return [
            keep_score_in_range(start + position * change + random_change())
            for position in range(num_scores)
        ]

    start = random_numbers.uniform(*DECREASING_START_RANGE)

    return [
        keep_score_in_range(start - position * change + random_change())
        for position in range(num_scores)
    ]


# Run the app's own baseline rule on every history with one setting
def evaluate_one_setting(prev_scores_taken, change_threshold):
    personal_baseline.PREV_NUM_BASELINE_SCORES_TAKEN = prev_scores_taken
    personal_baseline.RISK_CHANGE_THRESHOLD = change_threshold

    # Every setting is tested on the same histories because the seed is fixed
    random_numbers = random.Random(SEED)

    what_the_app_said = {
        history_type: {"increasing": 0, "decreasing": 0, "stable": 0, "insufficient": 0}
        for history_type in HISTORY_TYPES
    }

    for history_type in HISTORY_TYPES:
        for _ in range(HISTORIES_PER_TYPE):
            history = generate_history(history_type, HISTORY_LENGTH, random_numbers)
            current_score = history[-1]
            prev_scores = history[:-1]

            result = personal_baseline.compare_with_personal_baseline(
                current_score, prev_scores
            )
            what_the_app_said[history_type][result.risk_change_direction] += 1

    # The share of increasing and decreasing histories that were caught
    changes_caught = (
        what_the_app_said["increasing"]["increasing"]
        + what_the_app_said["decreasing"]["decreasing"]
    )
    changes_caught_percent = changes_caught / (HISTORIES_PER_TYPE * 2) * 100

    # The share of stable histories that were wrongly shown as a change
    stable_marked_as_change = (
        HISTORIES_PER_TYPE - what_the_app_said["stable"]["stable"]
    )
    false_change_percent = stable_marked_as_change / HISTORIES_PER_TYPE * 100

    return {
        "prev_scores_taken": prev_scores_taken,
        "change_threshold": change_threshold,
        "used_by_app": (
            prev_scores_taken == APP_PREV_SCORES_TAKEN
            and change_threshold == APP_RISK_CHANGE_THRESHOLD
        ),
        "changes_caught_percent": round(changes_caught_percent, 2),
        "false_change_percent": round(false_change_percent, 2),
        # The combined score is the average of changes caught and stable histories left as stable
        "combined_score_percent": round(
            (changes_caught_percent + (100 - false_change_percent)) / 2, 2
        ),
        "what_the_app_said": what_the_app_said,
    }


def save_table(all_results):
    columns = [
        "rank",
        "prev_scores_taken",
        "change_threshold",
        "used_by_app",
        "changes_caught_percent",
        "false_change_percent",
        "combined_score_percent",
    ]

    best_first = sorted(
        all_results,
        key=lambda result: (-result["combined_score_percent"], result["prev_scores_taken"]),
    )

    with TABLE_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()

        for rank, result in enumerate(best_first, start=1):
            writer.writerow({"rank": rank, **{key: result[key] for key in columns[1:]}})


def main():
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("AI.FIT personal baseline settings evaluation")
    print(
        f"Used by the app - {APP_PREV_SCORES_TAKEN} previous scores, "
        f"change threshold {APP_RISK_CHANGE_THRESHOLD}"
    )
    print(f"Settings to test - {len(PREV_SCORE_COUNTS_TESTED) * len(CHANGE_THRESHOLDS_TESTED)}")
    print()

    all_results = []

    for prev_scores_taken in PREV_SCORE_COUNTS_TESTED:
        for change_threshold in CHANGE_THRESHOLDS_TESTED:
            result = evaluate_one_setting(prev_scores_taken, change_threshold)
            all_results.append(result)

            print(
                f"  {prev_scores_taken} previous scores, change threshold {change_threshold} - "
                f"{result['changes_caught_percent']}% of changes caught, "
                f"{result['false_change_percent']}% of stable histories marked as a change, "
                f"combined score {result['combined_score_percent']}%"
            )

    # Put the app's own settings back once the test is finished
    personal_baseline.PREV_NUM_BASELINE_SCORES_TAKEN = APP_PREV_SCORES_TAKEN
    personal_baseline.RISK_CHANGE_THRESHOLD = APP_RISK_CHANGE_THRESHOLD

    used_by_app = next(result for result in all_results if result["used_by_app"])
    best = max(all_results, key=lambda result: result["combined_score_percent"])

    summary = {
        "evaluation": "AI.FIT personal baseline settings evaluation",
        "random_seed": SEED,
        "histories_per_type": HISTORIES_PER_TYPE,
        "random_variation": RANDOM_VARIATION,
        "change_per_checkin": list(CHANGE_PER_CHECKIN),
        "stable_start_range": list(STABLE_START_RANGE),
        "increasing_start_range": list(INCREASING_START_RANGE),
        "decreasing_start_range": list(DECREASING_START_RANGE),
        "prev_score_counts_tested": PREV_SCORE_COUNTS_TESTED,
        "change_thresholds_tested": CHANGE_THRESHOLDS_TESTED,
        "app_prev_scores_taken": APP_PREV_SCORES_TAKEN,
        "app_change_threshold": APP_RISK_CHANGE_THRESHOLD,
        "app_combined_score_percent": used_by_app["combined_score_percent"],
        "best_prev_scores_taken": best["prev_scores_taken"],
        "best_change_threshold": best["change_threshold"],
        "best_combined_score_percent": best["combined_score_percent"],
        "every_setting": all_results,
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    save_table(all_results)

    print()
    print(f"The app's settings give a combined score of {used_by_app['combined_score_percent']}%.")
    print(
        f"The best setting was {best['prev_scores_taken']} previous scores with a "
        f"change threshold of {best['change_threshold']}, at {best['combined_score_percent']}%."
    )
    print()
    print(f"Saved - {SUMMARY_PATH}")
    print(f"Saved - {TABLE_PATH}")


if __name__ == "__main__":
    main()

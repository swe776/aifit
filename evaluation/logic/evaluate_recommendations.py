# Section 5.5.3 tests the recommendation rules against Appendix B
import sys
from pathlib import Path

# Let this script use the shared helpers
sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "shared")
)

from paths import (
    DATA_DIRECTORY,
    PROJECT_ROOT,
    RESULTS_DIRECTORY,
)

import csv
import json
import re
from collections import Counter

from backend.app.logic.dropout_risk_score import (
    calc_dropout_risk,
)
from backend.app.logic.recommendation_rules import (
    build_recommendations,
)


RISK_GRID_PATH = DATA_DIRECTORY / "risk_grid.csv"

SUMMARY_PATH = (
    RESULTS_DIRECTORY
    / "recommendations.json"
)

# The expected output was written down before testing using the rules in Appendix B
EXPECTED_HEADLINES = {
    "high": "Your check-in suggests a higher risk of dropout.",
    "medium": "Your check-in suggests you might be starting to struggle.",
    "low": "",
}

LOW_RISK_POOR_MEAL_HEADLINE = "Your check-in looks okay but your meal might not be supporting your training."

# Advice is always given at high and medium risk
RISK_LEVELS_GIVEN_ADVICE = ("high", "medium")

EMOTIONAL_SIGNALS = {
    "burnout",
    "low motivation",
    "fatigue",
    "high motivation",
    "neutral",
}

MEAL_BANDS = {
    "balanced",
    "mixed",
    "poor",
}

RISK_LEVELS = {
    "low",
    "medium",
    "high",
}

# Words each tip must contain so the advice matches the signal that was detected
SIGNAL_ADVICE_WORDS = {
    "high": {
        "burnout": [
            "rest day",
            "intensity",
        ],
        "low motivation": [
            "goals",
            "plan out",
        ],
        "fatigue": [
            "lighter",
            "sleep",
        ],
    },
    "medium": {
        "fatigue": [
            "recovery",
        ],
        "high motivation": [
            "planning",
        ],
    },
}

# Words each meal tip must contain
MEAL_ADVICE_WORDS = {
    "poor": [
        "protein",
        "vegetables",
    ],
    "mixed": [
        "variety",
    ],
}

def normalise_text(value):
    return " ".join(
        str(value).strip().lower().split()
    )


# Match whole words only
def contains_phrase(text, phrase):
    pattern = (
        r"\b"
        + re.escape(phrase)
        + r"\b"
    )

    return bool(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
    )


# Read the 15 combinations from the reference risk grid and make sure each one is there exactly once
def read_risk_grid():
    if not RISK_GRID_PATH.is_file():
        raise FileNotFoundError(
            "The reference risk grid was not found. Expected - "
            f"{RISK_GRID_PATH}"
        )

    with RISK_GRID_PATH.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as grid_file:
        reader = csv.DictReader(grid_file)
        rows = list(reader)

    required_fields = {
        "emotion_label",
        "nutrition_category",
        "intended_risk_level",
    }
    missing_fields = required_fields - set(
        reader.fieldnames or []
    )

    if missing_fields:
        raise ValueError(
            "The reference risk grid is missing columns - "
            f"{sorted(missing_fields)}"
        )

    cases = []
    combinations = set()

    for row in rows:
        emotion = normalise_text(
            row["emotion_label"]
        )
        nutrition = normalise_text(
            row["nutrition_category"]
        )
        intended_level = normalise_text(
            row["intended_risk_level"]
        )

        if emotion not in EMOTIONAL_SIGNALS:
            raise ValueError(
                f"Unknown emotional signal in the risk grid - {emotion}"
            )

        if nutrition not in MEAL_BANDS:
            raise ValueError(
                "Unknown meal band in the risk grid - "
                f"{nutrition}"
            )

        if intended_level not in RISK_LEVELS:
            raise ValueError(
                "Unknown risk level in the risk grid - "
                f"{intended_level}"
            )

        combination = (
            emotion,
            nutrition,
        )

        if combination in combinations:
            raise ValueError(
                "This combination appears twice in the risk grid - "
                f"{emotion} with {nutrition}"
            )

        combinations.add(combination)
        cases.append({
            "emotion_label": emotion,
            "nutrition_category": nutrition,
            "intended_risk_level": intended_level,
        })

    expected_combinations = {
        (emotion, nutrition)
        for emotion in EMOTIONAL_SIGNALS
        for nutrition in MEAL_BANDS
    }

    if combinations != expected_combinations:
        raise ValueError(
            "The risk grid must contain each of the 15 emotional signal and nutrition combinations exactly once. Missing - "
            f"{sorted(expected_combinations - combinations)}. "
            "Unexpected - "
            f"{sorted(combinations - expected_combinations)}."
        )

    return sorted(
        cases,
        key=lambda case: (
            case["emotion_label"],
            case["nutrition_category"],
        ),
    )


# Check that one combination gets the right risk level and the expected advice
def check_grid_case(case):
    dropout_risk = calc_dropout_risk(
        case["emotion_label"],
        case["nutrition_category"],
    )

    recommendation = build_recommendations(dropout_risk)
    headline = str(
        recommendation.get("headline") or ""
    ).strip()
    tips = [
        str(tip).strip()
        for tip in recommendation.get("tips", [])
    ]
    combined_text = normalise_text(
        " ".join([headline, *tips])
    )

    intended_level = case["intended_risk_level"]

    low_risk_with_a_poor_meal = (
        intended_level == "low"
        and case["nutrition_category"] == "poor"
    )

    # At low risk advice is only expected when the meal is poor
    should_speak = (
        intended_level in RISK_LEVELS_GIVEN_ADVICE
        or low_risk_with_a_poor_meal
    )

    if low_risk_with_a_poor_meal:
        expected_headline = LOW_RISK_POOR_MEAL_HEADLINE
    else:
        expected_headline = EXPECTED_HEADLINES.get(intended_level, "")

    if should_speak:
        signal_advice_words = SIGNAL_ADVICE_WORDS.get(
            intended_level,
            {},
        ).get(
            case["emotion_label"],
            [],
        )
        meal_advice_words = MEAL_ADVICE_WORDS.get(
            case["nutrition_category"],
            [],
        )

        expected_output_given = (
            headline == expected_headline
            and len(tips) >= 1
            and all(tips)
            and all(
                contains_phrase(combined_text, keyword)
                for keyword in signal_advice_words + meal_advice_words
            )
        )
    else:
        # When no advice is expected the check-in must get no headline and no tips
        expected_output_given = (
            headline == ""
            and tips == []
        )

    return {
        "emotion_label": case["emotion_label"],
        "nutrition_category": case["nutrition_category"],
        "intended_risk_level": case["intended_risk_level"],
        "produced_risk_level": dropout_risk.dropout_risk_level,
        "risk_level_matches_grid": (
            dropout_risk.dropout_risk_level
            == case["intended_risk_level"]
        ),
        "headline": headline,
        "tip_count": len(tips),
        "tips_json": json.dumps(tips),
        "expected_output_given": expected_output_given,
    }


def count_passes(rows, field):
    return sum(
        bool(row[field])
        for row in rows
    )


# The four risk states tested with every combination and None means there is no baseline yet
RISK_CHANGE_DIRECTIONS = ["increasing", "decreasing", "stable", None]

INCREASING_RISK_PHRASE = "higher than your recent average"
DECREASING_RISK_PHRASE = "lower than your recent average"


# A simple baseline result so each risk change can be tested on its own
class StandInBaselineResult:
    def __init__(self, risk_change_direction):
        self.risk_change_direction = risk_change_direction


def expected_risk_change_output(risk_level, nutrition, direction):
    should_speak = (
        risk_level in RISK_LEVELS_GIVEN_ADVICE
        or nutrition == "poor"
        or direction == "increasing"
    )

    return should_speak, direction == "increasing"


# Test all 15 combinations across the four risk states which gives 60 cases
def build_risk_change_cases():
    results = []

    for emotion in sorted(EMOTIONAL_SIGNALS):
        for nutrition in sorted(MEAL_BANDS):
            dropout_risk = calc_dropout_risk(emotion, nutrition)

            for direction in RISK_CHANGE_DIRECTIONS:
                baseline = (
                    StandInBaselineResult(direction)
                    if direction is not None
                    else None
                )

                recommendation = build_recommendations(
                    dropout_risk, baseline=baseline
                )
                headline = str(
                    recommendation.get("headline") or ""
                ).strip()
                tips = [
                    str(tip).strip()
                    for tip in recommendation.get("tips", [])
                ]
                combined = normalise_text(
                    " ".join([headline, *tips])
                )

                speaks = bool(headline or tips)
                mentions_increase = INCREASING_RISK_PHRASE in combined
                mentions_decrease = DECREASING_RISK_PHRASE in combined

                should_speak, should_mention_increase = expected_risk_change_output(
                    dropout_risk.dropout_risk_level,
                    nutrition,
                    direction,
                )

                results.append({
                    "emotion_label": emotion,
                    "nutrition_category": nutrition,
                    "risk_level": dropout_risk.dropout_risk_level,
                    "direction": direction or "none",
                    "headline": headline,
                    "tips": tips,
                    "produced_any_output": speaks,
                    "mentions_the_increase": mentions_increase,
                    "mentions_the_decrease": mentions_decrease,
                    "expected_output_given": (
                        speaks == should_speak
                        and mentions_increase == should_mention_increase
                        and not mentions_decrease
                    ),
                })

    return results


# Check the repeated signal tip only appears when the same high risk signal shows up twice in the previous three check-ins
def build_repeat_signal_cases():
    cases = []

    for emotion in ("burnout", "low motivation"):
        for nutrition in ("mixed", "poor"):
            dropout_risk = calc_dropout_risk(emotion, nutrition)

            for recent, expected in (
                ([emotion, "neutral", emotion], True),
                ([emotion, "neutral", "fatigue"], False),
            ):
                output = build_recommendations(
                    dropout_risk, prev_emotional_signals=recent
                )
                text = normalise_text(
                    " ".join([
                        output.get("headline", ""),
                        *output.get("tips", []),
                    ])
                )
                found = "not the first recent check-in" in text

                cases.append({
                    "emotion_label": emotion,
                    "nutrition_category": nutrition,
                    "risk_level": dropout_risk.dropout_risk_level,
                    "prev_emotional_signals": recent,
                    "expected_repeat_advice": expected,
                    "repeat_advice_present": found,
                    "passed": found == expected,
                })

    return cases


def main():
    RESULTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    evaluated_cases = [
        check_grid_case(case)
        for case in read_risk_grid()
    ]

    def cases_at(level):
        return [
            case
            for case in evaluated_cases
            if case["intended_risk_level"] == level
        ]

    high_risk_cases = cases_at("high")
    medium_risk_cases = cases_at("medium")
    low_risk_cases = cases_at("low")

    trend_cases = build_risk_change_cases()
    increasing_cases = [
        case for case in trend_cases
        if case["direction"] == "increasing"
    ]
    decreasing_low_risk_cases = [
        case for case in trend_cases
        if case["direction"] == "decreasing"
        and case["risk_level"] == "low"
    ]
    repeat_cases = build_repeat_signal_cases()

    # Every group of checks has to pass for Objective 3 to be met
    checks = {
        "risk_grid": (
            count_passes(evaluated_cases, "risk_level_matches_grid"),
            len(evaluated_cases),
        ),
        "risk_changes": (
            count_passes(trend_cases, "expected_output_given"),
            len(trend_cases),
        ),
        "high_risk_advice": (
            count_passes(high_risk_cases, "expected_output_given"),
            len(high_risk_cases),
        ),
        "medium_risk_advice": (
            count_passes(medium_risk_cases, "expected_output_given"),
            len(medium_risk_cases),
        ),
        "low_risk_silence": (
            count_passes(low_risk_cases, "expected_output_given"),
            len(low_risk_cases),
        ),
        "repeat_signal_rule": (
            sum(case["passed"] for case in repeat_cases),
            len(repeat_cases),
        ),
        "increasing_risk": (
            sum(case["mentions_the_increase"] for case in increasing_cases),
            len(increasing_cases),
        ),
        "no_recommendations_for_a_decreasing_low_risk": (
            sum(not case["mentions_the_decrease"] for case in decreasing_low_risk_cases),
            len(decreasing_low_risk_cases),
        ),
    }

    all_checks_passed = all(
        passed == total for passed, total in checks.values()
    )

    summary = {
        "evaluation": "AI.FIT rule-based recommendation evaluation",
        "reference_grid_path": str(
            RISK_GRID_PATH.relative_to(PROJECT_ROOT)
        ),
        "evaluation_case_count": len(evaluated_cases),
        "intended_risk_level_counts": dict(
            Counter(
                case["intended_risk_level"]
                for case in evaluated_cases
            )
        ),
        "checks": {
            name: {
                "passed": passed,
                "total": total,
                "met": passed == total,
            }
            for name, (passed, total) in checks.items()
        },
        "all_checks_passed": all_checks_passed,
        "cases": evaluated_cases,
        "trend_cases": trend_cases,
        "repeat_signal_cases": repeat_cases,
    }

    with SUMMARY_PATH.open(
        "w",
        encoding="utf-8",
    ) as summary_file:
        json.dump(
            summary,
            summary_file,
            indent=2,
        )

    print("AI.FIT recommendation evaluation")

    for name, (passed, total) in checks.items():
        print(f"  {name.replace('_', ' ')} - {passed}/{total}")

    print(f"All checks passed - {all_checks_passed}")
    print()
    print(f"Summary - {SUMMARY_PATH.resolve()}")


if __name__ == "__main__":
    main()

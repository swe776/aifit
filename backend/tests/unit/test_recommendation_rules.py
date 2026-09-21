# Unit tests for the recommendation rules
import pytest

from backend.app.logic.dropout_risk_score import (
    calc_dropout_risk,
)
from backend.app.logic.personal_baseline import (
    compare_with_personal_baseline,
)
from backend.app.logic.recommendation_rules import (
    build_recommendations,
)


@pytest.mark.parametrize(
    (
        "emotion,nutrition,emotion_words,nutrition_words,expected_tip_count"
    ),
    [
        (
            "burnout",
            "poor",
            "rest day",
            "protein",
            3,
        ),
        (
            "burnout",
            "mixed",
            "rest day",
            "mix of foods",
            3,
        ),
        (
            "burnout",
            "balanced",
            "rest day",
            None,
            2,
        ),
        (
            "low motivation",
            "poor",
            "long term goals",
            "protein",
            3,
        ),
        (
            "low motivation",
            "mixed",
            "long term goals",
            "mix of foods",
            3,
        ),
        (
            "low motivation",
            "balanced",
            "long term goals",
            None,
            2,
        ),
        (
            "fatigue",
            "poor",
            "lighter",
            "protein",
            3,
        ),
    ],
)
def test_high_risk_gets_recommendations(
    emotion,
    nutrition,
    emotion_words,
    nutrition_words,
    expected_tip_count,
):
    dropout_risk = calc_dropout_risk(
        emotion,
        nutrition,
    )

    recommendation = build_recommendations(
        dropout_risk
    )

    assert dropout_risk.dropout_risk_level == "high"

    assert recommendation["headline"] == "Your check-in suggests a higher risk of dropout."

    assert len(recommendation["tips"]) == (
        expected_tip_count
    )

    assert any(
        emotion_words in tip
        for tip in recommendation["tips"]
    )

    if nutrition_words is not None:
        assert any(
            nutrition_words in tip
            for tip in recommendation["tips"]
        )


@pytest.mark.parametrize(
    "emotion,nutrition",
    [
        (
            "fatigue",
            "mixed",
        ),
        (
            "fatigue",
            "balanced",
        ),
    ],
)
def test_medium_risk_gets_advice(
    emotion,
    nutrition,
):

    dropout_risk = calc_dropout_risk(
        emotion,
        nutrition,
    )

    recommendation = build_recommendations(
        dropout_risk
    )

    assert dropout_risk.dropout_risk_level == "medium"

    assert recommendation["headline"] == "Your check-in suggests you might be starting to struggle."

    assert len(recommendation["tips"]) >= 1


def test_a_good_check_in_with_a_poor_meal_is_low_risk_but_still_hears_about_it():
    for emotion in ("high motivation", "neutral"):
        dropout_risk = calc_dropout_risk(emotion, "poor")
        recommendation = build_recommendations(dropout_risk)

        assert dropout_risk.dropout_risk_level == "low"

        assert recommendation["headline"] == "Your check-in looks okay but your meal might not be supporting your training."

        assert "struggl" not in recommendation["headline"].lower()

        assert len(recommendation["tips"]) == 1
        assert "protein" in recommendation["tips"][0]


@pytest.mark.parametrize(
    "emotion,nutrition",
    [
        (
            "high motivation",
            "mixed",
        ),
        (
            "high motivation",
            "balanced",
        ),
        (
            "neutral",
            "mixed",
        ),
        (
            "neutral",
            "balanced",
        ),
    ],
)
def test_low_risk_stays_silent(
    emotion,
    nutrition,
):

    dropout_risk = calc_dropout_risk(
        emotion,
        nutrition,
    )

    recommendation = build_recommendations(
        dropout_risk
    )

    assert dropout_risk.dropout_risk_level == "low"

    assert recommendation == {
        "headline": "",
        "tips": [],
    }


def test_low_risk_and_improving_says_nothing():
    dropout_risk = calc_dropout_risk(
        "neutral",
        "balanced",
    )

    baseline = compare_with_personal_baseline(
        dropout_risk.dropout_risk_score,
        [7.0, 7.5, 8.0],
    )

    recommendation = build_recommendations(
        dropout_risk,
        baseline,
    )

    assert baseline.risk_change_direction == "decreasing"
    assert recommendation["headline"] == ""
    assert recommendation["tips"] == []


def test_rising_risk_is_mentioned():
    dropout_risk = calc_dropout_risk(
        "burnout",
        "poor",
    )

    baseline = compare_with_personal_baseline(
        dropout_risk.dropout_risk_score,
        [2.0, 2.0, 2.0],
    )

    recommendation = build_recommendations(
        dropout_risk,
        baseline,
    )

    assert baseline.risk_change_direction == "increasing"

    assert any(
        "higher than your recent average" in tip
        for tip in recommendation["tips"]
    )


def test_repeated_signal_is_escalated():
    dropout_risk = calc_dropout_risk(
        "burnout",
        "balanced",
    )

    recommendation = build_recommendations(
        dropout_risk,
        None,
        ["burnout", "neutral", "burnout"],
    )

    assert any(
        "not the first recent check-in" in tip
        for tip in recommendation["tips"]
    )


def test_single_earlier_signal_is_not_escalated():
    dropout_risk = calc_dropout_risk(
        "burnout",
        "balanced",
    )

    recommendation = build_recommendations(
        dropout_risk,
        None,
        ["neutral", "fatigue", "burnout"],
    )

    assert not any(
        "not the first recent check-in" in tip
        for tip in recommendation["tips"]
    )


def test_tips_are_capped_and_never_repeat():
    dropout_risk = calc_dropout_risk(
        "burnout",
        "poor",
    )

    baseline = compare_with_personal_baseline(
        dropout_risk.dropout_risk_score,
        [2.0, 2.0, 2.0],
    )

    recommendation = build_recommendations(
        dropout_risk,
        baseline,
        ["burnout", "burnout", "burnout"],
    )

    tips = recommendation["tips"]

    assert len(tips) <= 3
    assert len(tips) == len(set(tips))


def test_same_check_in_always_gives_the_same_advice():
    dropout_risk = calc_dropout_risk(
        "low motivation",
        "mixed",
    )

    first = build_recommendations(
        dropout_risk,
        None,
        ["low motivation"],
    )

    for _ in range(5):
        assert build_recommendations(
            dropout_risk,
            None,
            ["low motivation"],
        ) == first

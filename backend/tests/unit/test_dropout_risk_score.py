# Unit tests for the dropout score and the risk level
import pytest

from backend.app.logic.dropout_risk_score import (
    EMOTIONAL_SIGNAL_POINTS,
    MEAL_BAND_POINTS,
    REFERENCE_RISK_GRID,
    calc_dropout_risk,
)


@pytest.mark.parametrize(
    (
        "emotion,nutrition,expected_score,expected_level"
    ),
    [
        (
            "burnout",
            "poor",
            8.5,
            "high",
        ),
        (
            "burnout",
            "mixed",
            7.75,
            "high",
        ),
        (
            "burnout",
            "balanced",
            6.88,
            "high",
        ),
        (
            "low motivation",
            "poor",
            8.5,
            "high",
        ),
        (
            "low motivation",
            "mixed",
            7.75,
            "high",
        ),
        (
            "low motivation",
            "balanced",
            6.88,
            "high",
        ),
        (
            "fatigue",
            "poor",
            6.25,
            "high",
        ),
        (
            "fatigue",
            "mixed",
            5.5,
            "medium",
        ),
        (
            "fatigue",
            "balanced",
            4.62,
            "medium",
        ),
        (
            "high motivation",
            "poor",
            3.62,
            "low",
        ),
        (
            "high motivation",
            "mixed",
            2.88,
            "low",
        ),
        (
            "high motivation",
            "balanced",
            2.0,
            "low",
        ),
        (
            "neutral",
            "poor",
            3.62,
            "low",
        ),
        (
            "neutral",
            "mixed",
            2.88,
            "low",
        ),
        (
            "neutral",
            "balanced",
            2.0,
            "low",
        ),
    ],
)
def test_dropout_risk_score_calculation(
    emotion,
    nutrition,
    expected_score,
    expected_level,
):
    result = calc_dropout_risk(
        emotion,
        nutrition,
    )

    assert (
        result.dropout_risk_score
        == expected_score
    )

    assert (
        result.dropout_risk_level
        == expected_level
    )


def test_labels_are_cleaned_before_scoring():
    result = calc_dropout_risk(
        "  Burnout  ",
        "  MIXED  ",
    )

    assert result.emotion_label == "burnout"
    assert result.nutrition_category == "mixed"
    assert result.dropout_risk_score == 7.75
    assert result.dropout_risk_level == "high"


@pytest.mark.parametrize(
    "emotion",
    [
        "confused",
        "stressed",
        "",
    ],
)
def test_unknown_emotion_is_rejected(
    emotion,
):
    with pytest.raises(ValueError):
        calc_dropout_risk(
            emotion,
            "balanced",
        )


@pytest.mark.parametrize(
    "nutrition",
    [
        "unknown",
        "healthy",
        "",
    ],
)
def test_unknown_meal_band_is_rejected(
    nutrition,
):
    with pytest.raises(ValueError):
        calc_dropout_risk(
            "neutral",
            nutrition,
        )


def test_a_certain_reading_scores_the_same_as_the_plain_label():
    with_confidences = calc_dropout_risk(
        "burnout",
        "poor",
        {"burnout": 1.0},
    )

    plain = calc_dropout_risk("burnout", "poor")

    assert with_confidences.dropout_risk_score == (
        plain.dropout_risk_score
    )


def test_an_unsure_reading_lands_between_the_labels():
    split_reading = calc_dropout_risk(
        "burnout",
        "mixed",
        {"burnout": 0.5, "fatigue": 0.5},
    )

    certain_burnout = calc_dropout_risk(
        "burnout", "mixed", {"burnout": 1.0}
    )
    certain_fatigue = calc_dropout_risk(
        "fatigue", "mixed", {"fatigue": 1.0}
    )

    assert (
        certain_fatigue.emotion_points
        < split_reading.emotion_points
        < certain_burnout.emotion_points
    )


def test_labels_the_scoring_does_not_know_are_ignored():
    result = calc_dropout_risk(
        "burnout",
        "poor",
        {"burnout": 1.0, "something else entirely": 0.4},
    )

    assert result.emotion_points == 8.5


def test_confidences_of_zero_are_skipped():
    result = calc_dropout_risk(
        "burnout",
        "poor",
        {"burnout": 1.0, "fatigue": 0.0, "neutral": -0.2},
    )

    assert result.emotion_points == 8.5


def test_nothing_usable_falls_back_to_the_plain_label():
    result = calc_dropout_risk(
        "burnout",
        "poor",
        {"not a label": 1.0},
    )

    assert result.emotion_points == 8.5
    assert result.meal_points == 8.5


def test_confidences_that_do_not_reach_one_are_pulled_to_the_middle():
    partial = calc_dropout_risk(
        "burnout", "poor", {"burnout": 0.6}
    )

    assert partial.emotion_points == 7.3
    assert partial.meal_points == 8.5


def test_confidences_adding_to_more_than_one_are_scaled_back():
    result = calc_dropout_risk(
        "burnout",
        "poor",
        {"burnout": 1.0, "fatigue": 1.0},
    )

    assert result.emotion_points == 7.0


# Read the Appendix A grid so the app can be checked against it
def read_appendix_a_grid():
    import csv
    from pathlib import Path

    grid_path = (
        Path(__file__).resolve().parents[3]
        / "evaluation" / "data" / "risk_grid.csv"
    )

    with grid_path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            (row["emotion_label"], row["nutrition_category"]):
                row["intended_risk_level"]
            for row in csv.DictReader(handle)
        }


def test_the_grid_has_every_combination_once():
    assert len(REFERENCE_RISK_GRID) == 15
    assert set(REFERENCE_RISK_GRID) == {
        (emotion, nutrition)
        for emotion in EMOTIONAL_SIGNAL_POINTS
        for nutrition in MEAL_BAND_POINTS
    }


@pytest.mark.parametrize(
    "emotion,nutrition",
    sorted(REFERENCE_RISK_GRID),
)
def test_each_check_in_gets_the_level_in_appendix_a(emotion, nutrition):
    expected = read_appendix_a_grid()[(emotion, nutrition)]

    assert REFERENCE_RISK_GRID[(emotion, nutrition)] == expected
    assert calc_dropout_risk(emotion, nutrition).dropout_risk_level == expected

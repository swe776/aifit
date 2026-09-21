# Unit tests for the personal baseline and the risk change
from backend.app.logic.personal_baseline import (
    calc_personal_baseline,
    compare_with_personal_baseline,
)


def test_baseline_needs_two_previous_scores():
    assert calc_personal_baseline([]) is None
    assert calc_personal_baseline([4.0]) is None
    assert calc_personal_baseline([4.0, 6.0]) == 5.0


def test_baseline_uses_latest_ten_scores():
    scores = [9.0, 1.0, 2.0, 3.0, 4.0, 5.0]

    assert calc_personal_baseline(scores) == 4.0


def test_increasing_risk():
    result = compare_with_personal_baseline(
        current_score=6.5,
        prev_scores=[4.0, 4.0],
    )

    assert result.baseline == 4.0
    assert result.difference_from_baseline == 2.5
    assert result.risk_change_direction == "increasing"
    assert result.risk_change_direction == "increasing"


def test_decreasing_risk():
    result = compare_with_personal_baseline(
        current_score=2.0,
        prev_scores=[4.0, 4.0],
    )

    assert result.risk_change_direction == "decreasing"
    assert result.risk_change_direction != "increasing"


def test_stable_risk():
    result = compare_with_personal_baseline(
        current_score=5.4,
        prev_scores=[4.0, 4.0],
    )

    assert result.risk_change_direction == "stable"


def test_the_threshold_to_count_as_change():
    increasing = compare_with_personal_baseline(
        current_score=5.5,
        prev_scores=[4.0, 4.0],
    )
    decreasing = compare_with_personal_baseline(
        current_score=2.5,
        prev_scores=[4.0, 4.0],
    )

    assert increasing.risk_change_direction == "increasing"
    assert decreasing.risk_change_direction == "decreasing"

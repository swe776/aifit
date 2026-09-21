from dataclasses import dataclass


# The previous ten scores and a threshold of 1.5 were selected after testing
PREV_NUM_BASELINE_SCORES_TAKEN = 10
RISK_CHANGE_THRESHOLD = 1.5


# Keep the baseline, the difference and the risk change together
@dataclass
class PersonalBaselineResult:
    baseline: float | None
    difference_from_baseline: float | None
    risk_change_direction: str


def calc_personal_baseline(
    prev_scores: list[float],
) -> float | None:

    # Use the ten most recent scores when there are that many
    recent_scores = prev_scores[-PREV_NUM_BASELINE_SCORES_TAKEN:]

    # At least two previous scores are needed before a baseline can be worked out
    if len(recent_scores) < 2:
        return None

    return sum(recent_scores) / len(recent_scores)


def compare_with_personal_baseline(
    current_score: float,
    prev_scores: list[float],
) -> PersonalBaselineResult:
    baseline = calc_personal_baseline(prev_scores)

    # There is no baseline yet so no risk change can be shown
    if baseline is None:
        return PersonalBaselineResult(
            baseline=None,
            difference_from_baseline=None,
            risk_change_direction="insufficient",
        )

    # The difference is the current score minus the baseline score
    difference_from_baseline = current_score - baseline

    # Risk is increasing when the score is 1.5 or more above the baseline and decreasing when it is 1.5 or more below
    if difference_from_baseline >= RISK_CHANGE_THRESHOLD:
        risk_change_direction = "increasing"
    elif difference_from_baseline <= -RISK_CHANGE_THRESHOLD:
        risk_change_direction = "decreasing"
    else:
        risk_change_direction = "stable"

    return PersonalBaselineResult(
        baseline=round(baseline, 2),
        difference_from_baseline=round(difference_from_baseline, 2),
        risk_change_direction=risk_change_direction,
    )

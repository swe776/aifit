from dataclasses import dataclass


# Emotion is given 0.75 and nutrition 0.25 because emotional signals are linked directly to dropout
EMOTION_WEIGHT = 0.75
MEAL_WEIGHT = 0.25


# Low risk signals carry 2.0, medium 5.5 and high 8.5 on a scale from 0 to 10
EMOTIONAL_SIGNAL_POINTS = {
    "burnout": 8.5,
    "low motivation": 8.5,
    "fatigue": 5.5,
    "high motivation": 2.0,
    "neutral": 2.0,
}

# Meal bands use the same points as the emotional signals
MEAL_BAND_POINTS = {
    "balanced": 2.0,
    "mixed": 5.5,
    "poor": 8.5,
}


# Any missing confidence is counted as the medium risk points of 5.5 but this does not happen because the model's confidence scores always add up to 1
MISSING_CONFIDENCE_POINTS = 5.5


# The risk level comes from the reference grid in Appendix A and not from the score
REFERENCE_RISK_GRID = {
    ("burnout", "balanced"): "high",
    ("burnout", "mixed"): "high",
    ("burnout", "poor"): "high",
    ("low motivation", "balanced"): "high",
    ("low motivation", "mixed"): "high",
    ("low motivation", "poor"): "high",
    ("fatigue", "balanced"): "medium",
    ("fatigue", "mixed"): "medium",
    ("fatigue", "poor"): "high",
    ("high motivation", "balanced"): "low",
    ("high motivation", "mixed"): "low",
    ("high motivation", "poor"): "low",
    ("neutral", "balanced"): "low",
    ("neutral", "mixed"): "low",
    ("neutral", "poor"): "low",
}


# Keep everything worked out for one check-in together
@dataclass
class DropoutRiskResult:
    emotion_label: str
    nutrition_category: str
    emotion_points: float
    meal_points: float
    dropout_risk_score: float
    dropout_risk_level: str


def expected_points(
    label_confidences: dict[str, float],
    label_points: dict[str, float],
) -> float | None:

    # Return nothing when there are no confidence scores to use
    if not label_confidences:
        return None

    weighted_points = 0.0
    confidence_used = 0.0

    # Multiply each label's points by its confidence score and add them together
    for label, confidence in label_confidences.items():
        label = str(label).strip().lower()

        # Skip labels that the scoring does not know
        if label not in label_points:
            continue

        confidence = float(confidence)

        # Skip labels with no confidence
        if confidence <= 0.0:
            continue

        weighted_points += label_points[label] * confidence
        confidence_used += confidence

    if confidence_used <= 0.0:
        return None

    # Confidence scores should add up to 1 for averaging so the code makes sure of that
    if confidence_used < 1.0:
        weighted_points += MISSING_CONFIDENCE_POINTS * (1.0 - confidence_used)

    elif confidence_used > 1.0:
        weighted_points = weighted_points / confidence_used

    return weighted_points


def calc_dropout_risk(
    emotion_label: str,
    nutrition_category: str,
    emotion_confidences: dict[str, float] | None = None,
) -> DropoutRiskResult:

    # Tidy the labels so small differences in spacing or capitals do not matter
    emotion_label = emotion_label.strip().lower()
    nutrition_category = nutrition_category.strip().lower()

    # Refuse labels that the application does not use
    if emotion_label not in EMOTIONAL_SIGNAL_POINTS:
        raise ValueError(
            f"Unknown emotional signal: {emotion_label}"
        )

    if nutrition_category not in MEAL_BAND_POINTS:
        raise ValueError(
            f"Unknown meal band: {nutrition_category}"
        )

    # Use the model's confidence scores to work out the emotion points
    emotion_points = expected_points(
        emotion_confidences,
        EMOTIONAL_SIGNAL_POINTS,
    )

    # A corrected signal has no confidence score so its fixed points are used instead
    if emotion_points is None:
        emotion_points = EMOTIONAL_SIGNAL_POINTS[emotion_label]

    # The meal band stays fixed because the user has already confirmed it
    meal_points = MEAL_BAND_POINTS[nutrition_category]

    emotion_points = round(emotion_points, 2)
    meal_points = round(meal_points, 2)

    # Combine the two using the weighted average
    dropout_risk_score = (
        emotion_points * EMOTION_WEIGHT
        + meal_points * MEAL_WEIGHT
    )

    dropout_risk_score = round(dropout_risk_score, 2)

    # Return the score with the risk level from the reference grid
    return DropoutRiskResult(
        emotion_label=emotion_label,
        nutrition_category=nutrition_category,
        emotion_points=emotion_points,
        meal_points=meal_points,
        dropout_risk_score=dropout_risk_score,
        dropout_risk_level=REFERENCE_RISK_GRID[
            (emotion_label, nutrition_category)
        ],
    )

from .dropout_risk_score import DropoutRiskResult


# Show at most three tips so the advice stays short
MAXIMUM_TIPS = 3

# Burnout and low motivation are the high risk signals
HIGH_RISK_SIGNALS = {"burnout", "low motivation"}

# A signal is repeated when it shows up in at least two of the previous three check-ins
REPEAT_SIGNAL_MIN_COUNT = 2
PREV_NUM_CHECKINS_FOR_REPEAT = 3


# These headlines are shown above the tips for each situation
HEADLINES = {
    "high": "Your check-in suggests a higher risk of dropout.",
    "medium": "Your check-in suggests you might be starting to struggle.",
    "low_risk_poor_meal": "Your check-in looks okay but your meal might not be supporting your training.",
    "low_but_increasing": "Your risk is still low but this check-in is higher than your recent average.",
}


# Every tip follows Appendix B and firm tips are for high risk while gentle tips are for medium risk
EMOTIONAL_SIGNAL_TIPS = {
    "burnout": {
        "firm": [
            "Consider taking a full rest day before your next workout session.",
            "Consider reducing the intensity or duration of one workout this week.",
        ],
        "gentle": [
            "Consider making one session this week easier than planned.",
        ],
    },
    "low motivation": {
        "firm": [
            "Think about your long term goals and keep going.",
            "Consider reducing the intensity or duration of one workout this week and plan out your next workout session.",
        ],
        "gentle": [
            "Try setting one small goal for your next workout.",
        ],
    },
    "fatigue": {
        "firm": [
            "Consider keeping your next workout lighter and giving more time for recovery.",
            "Try to get a good night of sleep before your next workout session and maintain a good sleep routine.",
        ],
        "gentle": [
            "Consider giving a little more time for recovery before your next session.",
        ],
    },
    "high motivation": {
        "firm": [
            "Consider planning your next workout while your motivation is high.",
        ],
        "gentle": [
            "Consider planning your next workout while your motivation is high.",
        ],
    },
    "neutral": {
        "firm": [
            "Continue following your routine.",
        ],
        "gentle": [
            "Continue following your routine.",
        ],
    },
}


# Tips for a poor or mixed meal band
MEAL_BAND_TIPS = {
    "poor": "Consider adding carbohydrates for recovery, protein for muscle repair and vegetables for vitamins and minerals.",
    "mixed": "Your meal shows a mix of foods. Consider adding more variety where possible.",
}


# Tip for when the check-in is higher than the user's recent average
RISK_CHANGE_TIPS = {
    "increasing": "This check-in is higher than your recent average so you might want to take it easier.",
}


# Tip for when the same high risk signal keeps coming back
REPEAT_SIGNAL_TIP = "This is not the first recent check-in showing high risk. Consider changing something in your routine or add something you can look forward to."


def count_repeat_signal(
    emotion_label: str,
    prev_emotional_signals: list[str] | None,
) -> int:

    if not prev_emotional_signals:
        return 0

    # Only look at the previous three check-ins
    window = prev_emotional_signals[-PREV_NUM_CHECKINS_FOR_REPEAT:]

    return sum(
        1 for label in window
        if label and label.strip().lower() == emotion_label
    )


def build_recommendations(
    dropout_risk: DropoutRiskResult,
    baseline=None,
    prev_emotional_signals: list[str] | None = None,
) -> dict:

    risk_level = dropout_risk.dropout_risk_level
    emotion_label = dropout_risk.emotion_label
    nutrition_category = dropout_risk.nutrition_category

    # There is no risk change when the user has no baseline yet
    risk_change_direction = getattr(baseline, "risk_change_direction", None)

    # At low risk, advice is only given when the risk is increasing or the meal is poor
    if risk_level == "low":
        if risk_change_direction == "increasing":
            tips = [RISK_CHANGE_TIPS["increasing"]]

            if nutrition_category == "poor":
                tips.append(MEAL_BAND_TIPS["poor"])

            return {
                "headline": HEADLINES["low_but_increasing"],
                "tips": tips,
            }

        if nutrition_category == "poor":
            return {
                "headline": HEADLINES["low_risk_poor_meal"],
                "tips": [MEAL_BAND_TIPS["poor"]],
            }

        # No advice is given for any other low risk check-in
        return {"headline": "", "tips": []}

    # Use firm tips at high risk and gentle tips at medium risk
    advice_tone = "firm" if risk_level == "high" else "gentle"

    headline = HEADLINES[risk_level]

    tips: list[str] = []

    repeat_count = count_repeat_signal(emotion_label, prev_emotional_signals)

    # Warn the user when the same high risk signal is repeated
    if (
        emotion_label in HIGH_RISK_SIGNALS
        and repeat_count >= REPEAT_SIGNAL_MIN_COUNT
    ):
        tips.append(REPEAT_SIGNAL_TIP)

    # Warn the user when their risk is increasing
    if risk_change_direction == "increasing":
        tips.append(RISK_CHANGE_TIPS["increasing"])

    # Add the tips for the emotional signal that was detected
    tips.extend(EMOTIONAL_SIGNAL_TIPS[emotion_label][advice_tone])

    # Add a meal tip when the band is poor or mixed
    if nutrition_category in MEAL_BAND_TIPS:
        tips.append(MEAL_BAND_TIPS[nutrition_category])

    seen: set[str] = set()
    ordered_tips = []

    # Remove any tip that is given twice and keep the order
    for tip in tips:
        if tip not in seen:
            seen.add(tip)
            ordered_tips.append(tip)

    return {
        "headline": headline,
        "tips": ordered_tips[:MAXIMUM_TIPS],
    }

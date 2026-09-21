# Unit tests for unusual inputs and edge cases across the app
import pytest

from backend.app.logic.personal_baseline import compare_with_personal_baseline
from backend.app.logic.dropout_risk_score import (
    calc_dropout_risk,
)
from backend.app.logic.meal_band_rules import (
    calc_band_from_reading,
    photo_reject_reason,
)
from backend.app.logic.recommendation_rules import (
    build_recommendations,
    count_repeat_signal,
)
from backend.app.routers import checkin_routes

from ..integration.test_api import create_test_checkin


@pytest.mark.parametrize(
    "emotion",
    [
        "  BURNOUT  ",
        "Burnout",
        "bUrNoUt",
    ],
)
def test_untidy_labels_are_still_understood(emotion):
    result = calc_dropout_risk(emotion, "  POOR  ")

    assert result.emotion_label == "burnout"
    assert result.nutrition_category == "poor"


@pytest.mark.parametrize(
    "emotion,nutrition",
    [
        ("", "poor"),
        ("burnout", ""),
        ("sad", "poor"),
        ("burnout", "greasy"),
        ("   ", "poor"),
    ],
)
def test_labels_the_system_does_not_know_are_refused(
    emotion,
    nutrition,
):
    with pytest.raises(ValueError):
        calc_dropout_risk(emotion, nutrition)


def test_every_combination_produces_a_usable_result():
    emotions = [
        "burnout",
        "low motivation",
        "fatigue",
        "high motivation",
        "neutral",
    ]

    for emotion in emotions:
        for nutrition in ("balanced", "mixed", "poor"):
            result = calc_dropout_risk(emotion, nutrition)

            assert 2.0 <= result.dropout_risk_score <= 8.5
            assert result.dropout_risk_level in (
                "low",
                "medium",
                "high",
            )


def test_a_change_of_exactly_the_threshold_counts():
    increasing = compare_with_personal_baseline(5.5, [4.0, 4.0])
    decreasing = compare_with_personal_baseline(2.5, [4.0, 4.0])

    assert increasing.difference_from_baseline == 1.5
    assert increasing.risk_change_direction == "increasing"
    assert decreasing.difference_from_baseline == -1.5
    assert decreasing.risk_change_direction == "decreasing"


def test_a_change_just_under_the_threshold_is_stable():
    assert compare_with_personal_baseline(
        5.49, [4.0, 4.0]
    ).risk_change_direction == "stable"

    assert compare_with_personal_baseline(
        2.51, [4.0, 4.0]
    ).risk_change_direction == "stable"


@pytest.mark.parametrize("previous", [[], [4.0]])
def test_too_little_history_gives_no_direction(previous):
    result = compare_with_personal_baseline(8.5, previous)

    assert result.baseline is None
    assert result.risk_change_direction == "insufficient"
    assert result.risk_change_direction != "increasing"


def test_increasing_is_only_shown_when_risk_goes_up():
    assert compare_with_personal_baseline(
        8.5, [2.0, 2.0]
    ).risk_change_direction == "increasing"

    assert compare_with_personal_baseline(
        2.0, [8.5, 8.5]
    ).risk_change_direction != "increasing"


@pytest.mark.parametrize(
    "history",
    [
        None,
        [],
        [""],
        [None],
        ["", None, ""],
    ],
)
def test_empty_or_broken_history_does_not_break_the_advice(history):
    dropout_risk = calc_dropout_risk("burnout", "poor")

    result = build_recommendations(dropout_risk, None, history)

    assert result["headline"]
    assert result["tips"]


def test_only_the_last_three_check_ins_count_as_a_repeat():
    assert count_repeat_signal(
        "burnout",
        ["burnout", "burnout", "neutral", "neutral", "neutral"],
    ) == 0

    assert count_repeat_signal(
        "burnout",
        ["neutral", "neutral", "burnout", "neutral", "burnout"],
    ) == 2


def test_a_repeated_signal_is_matched_regardless_of_spacing():
    assert count_repeat_signal(
        "burnout",
        ["  BURNOUT ", "Burnout", "neutral"],
    ) == 2


def test_advice_never_exceeds_three_tips_in_any_situation():
    emotions = [
        "burnout",
        "low motivation",
        "fatigue",
        "high motivation",
        "neutral",
    ]

    for emotion in emotions:
        for nutrition in ("balanced", "mixed", "poor"):
            dropout_risk = calc_dropout_risk(emotion, nutrition)

            baseline = compare_with_personal_baseline(
                dropout_risk.dropout_risk_score,
                [2.0, 2.0, 2.0],
            )

            result = build_recommendations(
                dropout_risk,
                baseline,
                [emotion, emotion, emotion],
            )

            tips = result["tips"]

            assert len(tips) <= 3
            assert len(tips) == len(set(tips))
            assert all(tip.strip() for tip in tips)


@pytest.mark.parametrize(
    "caption",
    ["", "   ", "!!!", "...", "12345"],
)
def test_a_caption_with_no_words_matches_nothing(caption):
    assert calc_band_from_reading(caption) is None
    assert photo_reject_reason(caption) != ""


@pytest.mark.parametrize(
    "caption",
    [
        "A photo of a cup of coffee on a table",
        "A photo of a glass of water sitting on a table",
        "A photo of a cup of tea on a counter with a sticker",
    ],
)
def test_a_photograph_of_only_a_drink_is_refused_as_a_drink(caption):
    assert photo_reject_reason(caption) != ""
    assert photo_reject_reason(caption) == "drink"


def test_a_photograph_of_something_inedible_is_refused_as_not_food():
    caption = "A photo of a piece of plastic sitting on a table"

    assert photo_reject_reason(caption) != ""
    assert photo_reject_reason(caption) == "not food"


def test_a_photograph_of_food_gives_no_refusal_reason():
    assert photo_reject_reason(
        "A photo of a bowl of cereal and bananas"
    ) == ""


def test_a_biscuit_is_let_through_even_though_it_is_not_a_meal():
    assert photo_reject_reason("A photo of biscuits on a plate") == ""
    assert photo_reject_reason(
        "A photo of biscuits on a plate"
    ) == ""


def test_a_caption_naming_two_kinds_of_food_is_counted_not_averaged():
    assert calc_band_from_reading(
        "a salad and a slice of chocolate cake"
    ) == "poor"


def test_part_of_a_word_does_not_count_as_a_match():
    assert calc_band_from_reading("frieszzz") is None
    assert calc_band_from_reading("saladbowl") is None


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Grilled Salmon", "mixed"),
        ("grilled-salmon", "mixed"),
        ("  FRENCH_FRIES  ", "poor"),
        ("french fries", "poor"),
        ("something nobody has heard of", None),
        ("", None),
    ],
)
def test_food_labels_are_tidied_before_sorting(label, expected):
    assert calc_band_from_reading(label) == expected


@pytest.mark.parametrize(
    "transcript",
    ["", "  ", "ab", "  a  "],
)
def test_a_transcript_that_is_too_short_is_refused(
    client,
    account_headers,
    transcript,
):
    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={"transcript": transcript},
        files={
            "image": ("m.jpg", b"test image", "image/jpeg"),
        },
    )

    assert response.status_code == 422


# A real check-in that is exactly at the 2000 character limit
def long_but_real_transcript() -> str:
    sentence = "Training has been hard this week and I feel tired after every session but I want to keep going. "

    return (sentence * 40)[:2000]


def test_a_transcript_at_the_length_limit_is_accepted(
    client,
    account_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        checkin_routes,
        "detect_emotional_signal",
        lambda _: {
            "label": "neutral",
            "confidence": 0.9,
            "scores": {},
        },
    )
    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        lambda _: {
            "food_label": "meal",
            "nutrition_category": "mixed",
        },
    )

    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={"transcript": long_but_real_transcript()},
        files={
            "image": ("m.jpg", b"test image", "image/jpeg"),
        },
    )

    assert response.status_code == 201


def test_an_uppercase_file_extension_is_accepted(
    client,
    account_headers,
    monkeypatch,
):

    monkeypatch.setattr(
        checkin_routes,
        "detect_emotional_signal",
        lambda _: {
            "label": "neutral",
            "confidence": 0.9,
            "scores": {},
        },
    )
    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        lambda _: {
            "food_label": "meal",
            "nutrition_category": "mixed",
        },
    )

    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I trained today and felt fine.",
        },
        files={
            "image": (
                "IMG_1234.JPG",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 201


def test_a_file_with_no_extension_is_refused(
    client,
    account_headers,
):
    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I trained today and felt fine.",
        },
        files={
            "image": ("photo", b"test", "image/jpeg"),
        },
    )

    assert response.status_code == 400


def test_working_on_a_deleted_check_in_gives_not_found(
    client,
    account_headers,
    monkeypatch,
):
    checkin = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="poor",
    ).json()

    client.delete(
        f"/api/checkins/{checkin['id']}",
        headers=account_headers,
    )

    for call in (
        lambda: client.delete(
            f"/api/checkins/{checkin['id']}",
            headers=account_headers,
        ),
        lambda: client.patch(
            f"/api/checkins/{checkin['id']}/correction",
            headers=account_headers,
            json={"emotion_label": "fatigue"},
        ),
        lambda: client.post(
            f"/api/checkins/{checkin['id']}/feedback",
            headers=account_headers,
            json={"helpful": True},
        ),
    ):
        assert call().status_code == 404


def test_a_check_in_that_does_not_exist_gives_not_found(
    client,
    account_headers,
):
    assert client.delete(
        "/api/checkins/999999",
        headers=account_headers,
    ).status_code == 404


def test_feedback_can_be_changed_afterwards(
    client,
    account_headers,
    monkeypatch,
):
    checkin = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="poor",
    ).json()

    client.post(
        f"/api/checkins/{checkin['id']}/feedback",
        headers=account_headers,
        json={"helpful": True, "feedback_text": "good"},
    )

    changed = client.post(
        f"/api/checkins/{checkin['id']}/feedback",
        headers=account_headers,
        json={"helpful": False, "feedback_text": "not good"},
    )

    assert changed.status_code == 200
    assert changed.json()["recommendation_helpful"] is False
    assert changed.json()["feedback_text"] == "not good"


def test_feedback_with_no_written_comment_is_accepted(
    client,
    account_headers,
    monkeypatch,
):
    checkin = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="poor",
    ).json()

    response = client.post(
        f"/api/checkins/{checkin['id']}/feedback",
        headers=account_headers,
        json={"helpful": True},
    )

    assert response.status_code == 200
    assert response.json()["feedback_text"] is None


def test_feedback_that_is_only_spaces_is_stored_as_nothing(
    client,
    account_headers,
    monkeypatch,
):
    checkin = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="poor",
    ).json()

    response = client.post(
        f"/api/checkins/{checkin['id']}/feedback",
        headers=account_headers,
        json={"helpful": True, "feedback_text": "     "},
    )

    assert response.status_code == 200
    assert not response.json()["feedback_text"]


def test_accepting_the_privacy_notice_twice_is_harmless(
    client,
    account_headers,
):
    first = client.post(
        "/api/accounts/privacy-notice",
        headers=account_headers,
    )
    second = client.post(
        "/api/accounts/privacy-notice",
        headers=account_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200


def test_an_email_is_matched_regardless_of_spacing_and_case(
    client,
):
    client.post(
        "/api/accounts/register",
        json={
            "email": "Daniel@Gmail.com",
            "display_name": "Daniel",
            "password": "password123",
        },
    )

    duplicate = client.post(
        "/api/accounts/register",
        json={
            "email": "daniel@gmail.com",
            "display_name": "Daniel",
            "password": "password123",
        },
    )

    assert duplicate.status_code == 409

    login = client.post(
        "/api/accounts/login",
        data={
            "username": "DANIEL@GMAIL.COM",
            "password": "password123",
        },
    )

    assert login.status_code == 200


def test_heic_is_offered_in_the_file_picker():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3]
        / "frontend" / "src" / "features" / "MealPhotoInput.jsx"
    ).read_text(encoding="utf-8")
    accept_line = next(line for line in source.splitlines() if "accept=" in line)
    assert ".heic" in accept_line
    assert ".heif" in accept_line


def test_the_dashboard_shows_corrected_signals():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3]
        / "frontend"
        / "src"
        / "features"
        / "DashboardScreen.jsx"
    ).read_text(encoding="utf-8")

    assert "corrected_emotion_label" in source
    assert "corrected_nutrition_category" in source


# Read a frontend file so its behaviour can be checked from here
def _frontend(name):
    from pathlib import Path

    return (
        Path(__file__).resolve().parents[3]
        / "frontend" / "src" / name
    ).read_text(encoding="utf-8")


def test_the_check_in_button_cannot_be_double_submitted():
    source = _frontend("features/CheckInScreen.jsx")

    assert "useRef" in source
    assert "submitting.current" in source
    assert source.index("if (submitting.current)") < source.index(
        "await createCheckin"
    )


def test_an_expired_session_returns_the_user_to_sign_in():
    api = _frontend("api.js")
    auth = _frontend("auth.jsx")

    assert "setSessionExpiredHandler" in api
    assert "response.status === 401" in api
    assert "setSessionExpiredHandler" in auth


def test_a_server_that_is_down_says_so():
    api = _frontend("api.js")

    assert "Could not reach AI.FIT" in api
    assert "response.status >= 500" in api

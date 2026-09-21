# Integration tests that follow whole check-ins from upload to advice using test replacement models
import os

from backend.app.routers import checkin_routes

from .test_api import (
    create_test_checkin,
    register_and_accept,
)


# Make a check-in with a chosen signal and meal band
def make_checkin(
    client,
    headers,
    monkeypatch,
    emotion,
    nutrition,
):
    response = create_test_checkin(
        client,
        headers,
        monkeypatch,
        emotion_label=emotion,
        nutrition_category=nutrition,
    )

    assert response.status_code == 201

    return response.json()


def test_advice_talks_about_a_rising_score(
    client,
    account_headers,
    monkeypatch,
):

    for _ in range(3):
        make_checkin(
            client,
            account_headers,
            monkeypatch,
            "neutral",
            "balanced",
        )

    latest = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "burnout",
        "poor",
    )

    assert latest["dropout_risk_level"] == "high"

    assert any(
        "higher than your recent average" in tip
        for tip in latest["recommendation_tips"]
    )


def test_advice_notices_a_repeated_signal(
    client,
    account_headers,
    monkeypatch,
):

    for _ in range(2):
        make_checkin(
            client,
            account_headers,
            monkeypatch,
            "burnout",
            "balanced",
        )

    third = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "burnout",
        "balanced",
    )

    assert any(
        "not the first recent check-in" in tip
        for tip in third["recommendation_tips"]
    )


def test_a_first_check_in_has_no_trend_wording(
    client,
    account_headers,
    monkeypatch,
):

    first = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "burnout",
        "poor",
    )

    assert not any(
        "recent average" in tip
        for tip in first["recommendation_tips"]
    )


def test_only_the_ten_most_recent_scores_set_the_baseline(
    client,
    account_headers,
    monkeypatch,
):

    for _ in range(2):
        make_checkin(
            client,
            account_headers,
            monkeypatch,
            "burnout",
            "poor",
        )

    for _ in range(12):
        make_checkin(
            client,
            account_headers,
            monkeypatch,
            "neutral",
            "balanced",
        )

    stats = client.get(
        "/api/checkins/stats",
        headers=account_headers,
    ).json()

    assert stats["personal_baseline"] == 2.0


def test_feedback_on_another_users_checkin_is_refused(
    client,
    account_headers,
    monkeypatch,
):
    owner_checkin = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "burnout",
        "poor",
    )

    other = register_and_accept(
        client,
        "leo@gmail.com",
    )

    response = client.post(
        (
            f"/api/checkins/"
            f"{owner_checkin['id']}/feedback"
        ),
        headers=other,
        json={"helpful": True},
    )

    assert response.status_code == 404


def test_deleting_another_users_checkin_is_refused(
    client,
    account_headers,
    monkeypatch,
):
    owner_checkin = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "burnout",
        "poor",
    )

    other = register_and_accept(
        client,
        "leo@gmail.com",
    )

    response = client.delete(
        f"/api/checkins/{owner_checkin['id']}",
        headers=other,
    )

    assert response.status_code == 404

    history = client.get(
        "/api/checkins",
        headers=account_headers,
    ).json()

    assert len(history) == 1


def test_a_missing_token_is_refused(client):
    response = client.get("/api/checkins")

    assert response.status_code in (401, 403)


def test_deleting_removes_it_from_trend_and_statistics(
    client,
    account_headers,
    monkeypatch,
):
    keep = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "neutral",
        "balanced",
    )

    remove = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "burnout",
        "poor",
    )

    before = client.get(
        "/api/checkins/stats",
        headers=account_headers,
    ).json()

    assert before["total_checkins"] == 2
    assert before["high_risk_checkins"] == 1

    client.delete(
        f"/api/checkins/{remove['id']}",
        headers=account_headers,
    )

    after = client.get(
        "/api/checkins/stats",
        headers=account_headers,
    ).json()

    trend = client.get(
        "/api/checkins/trend",
        headers=account_headers,
    ).json()

    assert after["total_checkins"] == 1
    assert after["high_risk_checkins"] == 0
    assert len(trend) == 1
    assert trend[0]["dropout_risk_score"] == (
        keep["dropout_risk_score"]
    )
    assert trend[0]["dropout_risk_level"] == "low"


def test_a_meal_band_cannot_be_set_directly(
    client,
    account_headers,
    monkeypatch,
):

    checkin = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "burnout",
        "poor",
    )

    client.patch(
        (
            f"/api/checkins/"
            f"{checkin['id']}/correction"
        ),
        headers=account_headers,
        json={
            "nutrition_category": "balanced",
            "corrected_nutrition_category": "balanced",
        },
    )

    after = client.get(
        "/api/checkins",
        headers=account_headers,
    ).json()[0]

    assert after["nutrition_category"] == "poor"
    assert after["corrected_nutrition_category"] is None


def test_an_empty_correction_changes_nothing(
    client,
    account_headers,
    monkeypatch,
):
    checkin = make_checkin(
        client,
        account_headers,
        monkeypatch,
        "burnout",
        "poor",
    )

    response = client.patch(
        (
            f"/api/checkins/"
            f"{checkin['id']}/correction"
        ),
        headers=account_headers,
        json={},
    )

    assert response.status_code in (200, 422)

    after = client.get(
        "/api/checkins",
        headers=account_headers,
    ).json()[0]

    assert after["dropout_risk_score"] == (
        checkin["dropout_risk_score"]
    )


def test_the_uploaded_image_is_deleted_after_a_check_in(
    client,
    account_headers,
    monkeypatch,
):

    seen_paths = []
    real_analyse = checkin_routes.read_meal_photo

    def record_then_analyse(path):
        seen_paths.append(path)

        return {
            "food_label": "test meal",
            "nutrition_category": "poor",
        }

    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        record_then_analyse,
    )
    monkeypatch.setattr(
        checkin_routes,
        "detect_emotional_signal",
        lambda _: {
            "label": "neutral",
            "confidence": 0.9,
            "scores": {},
        },
    )

    client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I am checking in after training.",
        },
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert seen_paths, "the image was never analysed"

    for path in seen_paths:
        assert not os.path.exists(path), (
            f"the uploaded image was left behind: {path}"
        )

    checkin_routes.read_meal_photo = real_analyse


def test_the_uploaded_image_is_deleted_when_analysis_fails(
    client,
    account_headers,
    monkeypatch,
):

    seen_paths = []

    def fail_after_recording(path):
        seen_paths.append(path)

        raise ValueError(
            "This photograph does not seem to show food."
        )

    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        fail_after_recording,
    )
    monkeypatch.setattr(
        checkin_routes,
        "detect_emotional_signal",
        lambda _: {
            "label": "neutral",
            "confidence": 0.9,
            "scores": {},
        },
    )

    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I am checking in after training.",
        },
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code >= 400
    assert seen_paths

    for path in seen_paths:
        assert not os.path.exists(path)

    history = client.get(
        "/api/checkins",
        headers=account_headers,
    ).json()

    assert history == []


def test_a_big_image_is_rejected(
    client,
    account_headers,
):

    from backend.app.config import settings

    too_big = b"x" * (
        (settings.max_image_mb + 1) * 1024 * 1024
    )

    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I am checking in after training.",
        },
        files={
            "image": (
                "meal.jpg",
                too_big,
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 413

    assert "MB" in response.json()["detail"]


def test_heic_photographs_are_accepted():
    from backend.app.config import ALLOWED_IMAGE_FILE_TYPES

    assert ".heic" in ALLOWED_IMAGE_FILE_TYPES
    assert ".heif" in ALLOWED_IMAGE_FILE_TYPES


def test_a_heic_file_can_be_opened():
    from pathlib import Path

    import pytest
    from PIL import Image

    from backend.app.models.meal_photo import allow_heic_photos

    sample = (
        Path(__file__).resolve().parents[3]
        / "evaluation" / "data" / "objective2_photos" / "mixed"
        / "ab240c6f450f90bd1744703a1208.jpeg"
    )
    if not sample.is_file():
        pytest.skip("the sample HEIC photograph is not present")
    allow_heic_photos()
    with Image.open(sample) as opened:
        assert opened.convert("RGB").size[0] > 0


def test_a_heic_upload_is_not_refused_on_its_extension(
    client, account_headers, monkeypatch,
):
    monkeypatch.setattr(checkin_routes, "read_meal_photo", lambda _: {
        "food_label": "test meal",
        "nutrition_category": "mixed",
    })
    monkeypatch.setattr(checkin_routes, "detect_emotional_signal", lambda _: {
        "label": "neutral", "confidence": 0.9, "scores": {},
    })
    response = client.post(
        "/api/checkins", headers=account_headers,
        data={"transcript": "I trained today and felt fine."},
        files={"image": ("photo.heic", b"fake heic bytes", "image/heic")},
    )
    assert response.status_code == 201

# Integration tests for the check-in routes and the database using test replacement models
from backend.app.logic.dropout_risk_score import calc_dropout_risk
from backend.app.db_models import Account
from backend.app.routers import (
    checkin_routes,
)


# Create a user who has accepted the privacy notice
def register_and_accept(
    client,
    email,
):
    register_response = client.post(
        "/api/accounts/register",
        json={
            "email": email,
            "display_name": "Leo",
            "password": "password123",
        },
    )

    token = register_response.json()[
        "access_token"
    ]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    client.post(
        "/api/accounts/privacy-notice",
        headers=headers,
    )

    return headers


# Make a check-in with set model answers so the result is known
def create_test_checkin(
    client,
    headers,
    monkeypatch,
    emotion_label="neutral",
    nutrition_category="mixed",
    transcript=(
        "I am checking in after my recent workout."
    ),
    emotion_scores=None,
):
    monkeypatch.setattr(
        checkin_routes,
        "detect_emotional_signal",
        lambda _: {
            "label": emotion_label,
            "confidence": 0.90,
            "scores": emotion_scores or {},
        },
    )

    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        lambda _: {
            "food_label": "test meal",
            "nutrition_category": (
                nutrition_category
            ),
        },
    )

    return client.post(
        "/api/checkins",
        headers=headers,
        data={
            "transcript": transcript,
        },
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )




def test_transcription_requires_privacy_notice(
    client,
):
    register_response = client.post(
        "/api/accounts/register",
        json={
            "email": "nina@gmail.com",
            "display_name": "Nina",
            "password": "password123",
        },
    )

    token = register_response.json()[
        "access_token"
    ]

    response = client.post(
        "/api/checkins/transcribe",
        headers={
            "Authorization": f"Bearer {token}"
        },
        files={
            "audio": (
                "voice.webm",
                b"test audio",
                "audio/webm",
            ),
        },
    )

    assert response.status_code == 403


def test_checkin_requires_privacy_notice(
    client,
):
    register_response = client.post(
        "/api/accounts/register",
        json={
            "email": "omar@gmail.com",
            "display_name": "Omar",
            "password": "password123",
        },
    )

    token = register_response.json()[
        "access_token"
    ]

    response = client.post(
        "/api/checkins",
        headers={
            "Authorization": f"Bearer {token}"
        },
        data={
            "transcript": "I feel okay after my workout.",
        },
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 403


def test_complete_checkin_flow(
    client,
    account_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        checkin_routes,
        "transcribe_audio",
        lambda _: "I feel burn out after training.",
    )

    transcript_response = client.post(
        "/api/checkins/transcribe",
        headers=account_headers,
        files={
            "audio": (
                "voice.webm",
                b"test audio",
                "audio/webm",
            ),
        },
    )

    assert transcript_response.status_code == 200

    assert transcript_response.json()[
        "transcript"
    ] == "I feel burn out after training."

    edited_transcript = "I feel burned out after training."

    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="poor",
        transcript=edited_transcript,
    )

    assert checkin_response.status_code == 201

    checkin = checkin_response.json()

    assert checkin["transcript"] == (
        edited_transcript
    )

    assert checkin["emotion_label"] == "burnout"

    assert checkin["nutrition_category"] == "poor"

    assert checkin["dropout_risk_score"] == (
        8.5
    )

    assert checkin["dropout_risk_level"] == "high"

    assert len(
        checkin["recommendation_tips"]
    ) == 3

    history_response = client.get(
        "/api/checkins",
        headers=account_headers,
    )

    trend_response = client.get(
        "/api/checkins/trend",
        headers=account_headers,
    )

    stats_response = client.get(
        "/api/checkins/stats",
        headers=account_headers,
    )

    assert len(history_response.json()) == 1
    assert len(trend_response.json()) == 1

    assert stats_response.json()[
        "total_checkins"
    ] == 1

    assert stats_response.json()[
        "high_risk_checkins"
    ] == 1

    feedback_response = client.post(
        (
            f"/api/checkins/"
            f"{checkin['id']}/feedback"
        ),
        headers=account_headers,
        json={
            "helpful": True,
            "feedback_text": "  The advice was useful.  ",
        },
    )

    assert feedback_response.status_code == 200

    assert feedback_response.json()[
        "recommendation_helpful"
    ] is True

    assert feedback_response.json()[
        "feedback_text"
    ] == "The advice was useful."

    delete_response = client.delete(
        f"/api/checkins/{checkin['id']}",
        headers=account_headers,
    )

    assert delete_response.status_code == 204

    final_history = client.get(
        "/api/checkins",
        headers=account_headers,
    )

    assert final_history.json() == []


def test_wrong_audio_type_is_rejected(
    client,
    account_headers,
):
    response = client.post(
        "/api/checkins/transcribe",
        headers=account_headers,
        files={
            "audio": (
                "voice.txt",
                b"not audio",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400


def test_empty_audio_is_rejected(
    client,
    account_headers,
):
    response = client.post(
        "/api/checkins/transcribe",
        headers=account_headers,
        files={
            "audio": (
                "voice.webm",
                b"",
                "audio/webm",
            ),
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == "The uploaded file is empty."


def test_big_audio_size_is_rejected(
    client,
    account_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        checkin_routes.settings,
        "max_audio_mb",
        1,
    )

    response = client.post(
        "/api/checkins/transcribe",
        headers=account_headers,
        files={
            "audio": (
                "voice.webm",
                b"x" * (1024 * 1024 + 1),
                "audio/webm",
            ),
        },
    )

    assert response.status_code == 413

    assert response.json()["detail"] == "The file must be smaller than 1 MB."


def test_no_clear_speech_is_rejected(
    client,
    account_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        checkin_routes,
        "transcribe_audio",
        lambda _: "",
    )

    response = client.post(
        "/api/checkins/transcribe",
        headers=account_headers,
        files={
            "audio": (
                "voice.webm",
                b"test audio",
                "audio/webm",
            ),
        },
    )

    assert response.status_code == 422

    assert response.json()["detail"] == "No clear speech was found in the recording. Please try again."


def test_audio_read_error_is_returned(
    client,
    account_headers,
    monkeypatch,
):
    def fail_transcription(_):
        raise ValueError(
            "The recording could not be opened."
        )

    monkeypatch.setattr(
        checkin_routes,
        "transcribe_audio",
        fail_transcription,
    )

    response = client.post(
        "/api/checkins/transcribe",
        headers=account_headers,
        files={
            "audio": (
                "voice.webm",
                b"test audio",
                "audio/webm",
            ),
        },
    )

    assert response.status_code == 422

    assert response.json()["detail"] == "The recording could not be opened."


def test_wrong_image_type_is_rejected(
    client,
    account_headers,
):
    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I feel okay after my workout.",
        },
        files={
            "image": (
                "meal.txt",
                b"not an image",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400


def test_empty_image_is_rejected(
    client,
    account_headers,
):
    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I feel okay after my workout.",
        },
        files={
            "image": (
                "meal.jpg",
                b"",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == "The uploaded file is empty."


def test_bad_image_is_rejected(
    client,
    account_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        checkin_routes,
        "detect_emotional_signal",
        lambda _: {
            "label": "neutral",
            "confidence": 0.90,
            "scores": {},
        },
    )

    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I feel okay after my workout.",
        },
        files={
            "image": (
                "meal.jpg",
                b"this is not an image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 422

    assert response.json()["detail"] == "The photograph could not be opened."


def test_short_transcript_is_rejected(
    client,
    account_headers,
):
    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "Hi",
        },
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 422


def test_long_transcript_is_rejected(
    client,
    account_headers,
):
    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "a" * 2001,
        },
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 422


def test_failed_meal_photo_reading_is_not_saved(
    client,
    account_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        checkin_routes,
        "detect_emotional_signal",
        lambda _: {
            "label": "neutral",
            "confidence": 0.90,
            "scores": {},
        },
    )

    def fail_nutrition(_):
        raise ValueError(
            "This image does might not contain food."
        )

    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        fail_nutrition,
    )

    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I feel okay after my workout.",
        },
        files={
            "image": (
                "grass.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 422

    history_response = client.get(
        "/api/checkins",
        headers=account_headers,
    )

    assert history_response.json() == []


def test_feedback_is_rejected_when_advice_not_given(
    client,
    account_headers,
    monkeypatch,
):
    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="neutral",
        nutrition_category="balanced",
    )

    checkin = checkin_response.json()

    assert checkin["dropout_risk_level"] == "low"

    response = client.post(
        (
            f"/api/checkins/"
            f"{checkin['id']}/feedback"
        ),
        headers=account_headers,
        json={
            "helpful": True,
            "feedback_text": "Test feedback",
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == "You can only rate advice on a check-in that gave advice."


def test_medium_risk_feedback_is_accepted(
    client,
    account_headers,
    monkeypatch,
):

    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="fatigue",
        nutrition_category="balanced",
    )

    checkin = checkin_response.json()

    assert checkin["dropout_risk_level"] == "medium"

    assert checkin["recommendation_tips"]

    response = client.post(
        (
            f"/api/checkins/"
            f"{checkin['id']}/feedback"
        ),
        headers=account_headers,
        json={
            "helpful": True,
            "feedback_text": "  useful advice  ",
        },
    )

    assert response.status_code == 200

    saved = response.json()

    assert saved["recommendation_helpful"] is True

    assert saved["feedback_text"] == "useful advice"


def test_checkins_are_private_between_users(
    client,
    account_headers,
    monkeypatch,
):
    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="poor",
    )

    checkin_id = checkin_response.json()[
        "id"
    ]

    other_headers = register_and_accept(
        client,
        "leo@gmail.com",
    )

    other_history = client.get(
        "/api/checkins",
        headers=other_headers,
    )

    assert other_history.json() == []

    feedback_response = client.post(
        (
            f"/api/checkins/"
            f"{checkin_id}/feedback"
        ),
        headers=other_headers,
        json={
            "helpful": True,
        },
    )

    assert feedback_response.status_code == 404

    delete_response = client.delete(
        f"/api/checkins/{checkin_id}",
        headers=other_headers,
    )

    assert delete_response.status_code == 404

    owner_history = client.get(
        "/api/checkins",
        headers=account_headers,
    )

    assert len(owner_history.json()) == 1


def test_dashboard_baseline_and_trend(
    client,
    account_headers,
    monkeypatch,
):
    create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="neutral",
        nutrition_category="balanced",
    )

    create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="fatigue",
        nutrition_category="mixed",
    )

    create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="poor",
    )

    stats = client.get(
        "/api/checkins/stats",
        headers=account_headers,
    ).json()

    trend = client.get(
        "/api/checkins/trend",
        headers=account_headers,
    ).json()

    assert stats["total_checkins"] == 3
    assert stats["high_risk_checkins"] == 1
    assert stats["average_risk_score"] == 5.33
    assert stats["personal_baseline"] == 3.75

    assert stats["difference_from_baseline"] == 4.75

    assert stats["trend_direction"] == "increasing"

    assert stats["trend_direction"] == "increasing"

    assert [
        point["dropout_risk_score"]
        for point in trend
    ] == [
        2.0,
        5.5,
        8.5,
    ]


def test_empty_dashboard_statistics(
    client,
    account_headers,
):
    stats = client.get(
        "/api/checkins/stats",
        headers=account_headers,
    ).json()

    assert stats["total_checkins"] == 0
    assert stats["high_risk_checkins"] == 0
    assert stats["average_risk_score"] == 0.0
    assert stats["personal_baseline"] is None

    assert stats[
        "difference_from_baseline"
    ] is None

    assert stats["trend_direction"] == "insufficient"

    assert stats["trend_direction"] != "increasing"


def test_checkin_correction_recalculates_risk(
    client,
    account_headers,
    monkeypatch,
):
    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="neutral",
        nutrition_category="poor",
    )

    assert checkin_response.status_code == 201

    original = checkin_response.json()

    assert original["dropout_risk_score"] == 3.62
    assert original["dropout_risk_level"] == "low"

    correction_response = client.patch(
        (
            f"/api/checkins/"
            f"{original['id']}/correction"
        ),
        headers=account_headers,
        json={
            "emotion_label": "burnout",
            "nutrition_category": "poor",
        },
    )

    assert correction_response.status_code == 200

    corrected = correction_response.json()

    assert corrected["emotion_label"] == "neutral"
    assert corrected["food_label"] == "test meal"

    assert corrected["nutrition_category"] == "poor"

    assert corrected["corrected_emotion_label"] == "burnout"

    assert corrected["corrected_nutrition_category"] == "poor"

    assert corrected["dropout_risk_score"] == 8.5
    assert corrected["dropout_risk_level"] == "high"

    assert corrected["recommendation_headline"] == "Your check-in suggests a higher risk of dropout."

    assert len(
        corrected["recommendation_tips"]
    ) == 3

    history = client.get(
        "/api/checkins",
        headers=account_headers,
    ).json()

    assert len(history) == 1

    assert history[0][
        "corrected_emotion_label"
    ] == "burnout"

    assert history[0][
        "dropout_risk_level"
    ] == "high"


def test_one_correction_uses_original_other_signal(
    client,
    account_headers,
    monkeypatch,
):
    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="neutral",
        nutrition_category="balanced",
    )

    checkin = checkin_response.json()

    response = client.patch(
        (
            f"/api/checkins/"
            f"{checkin['id']}/correction"
        ),
        headers=account_headers,
        json={
            "emotion_label": "fatigue",
        },
    )

    assert response.status_code == 200

    corrected = response.json()

    assert corrected["corrected_emotion_label"] == "fatigue"

    assert corrected["nutrition_category"] == "balanced"

    assert corrected["dropout_risk_score"] == 4.62
    assert corrected["dropout_risk_level"] == "medium"

    assert corrected["recommendation_headline"] == "Your check-in suggests you might be starting to struggle."

    assert len(
        corrected["recommendation_tips"]
    ) >= 1


def test_correction_resets_old_recommendation_feedback(
    client,
    account_headers,
    monkeypatch,
):
    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="balanced",
    )

    checkin = checkin_response.json()

    assert checkin["dropout_risk_level"] == "high"

    feedback_response = client.post(
        (
            f"/api/checkins/"
            f"{checkin['id']}/feedback"
        ),
        headers=account_headers,
        json={
            "helpful": True,
            "feedback_text": "Useful advice.",
        },
    )

    assert feedback_response.status_code == 200

    correction_response = client.patch(
        (
            f"/api/checkins/"
            f"{checkin['id']}/correction"
        ),
        headers=account_headers,
        json={
            "emotion_label": "neutral",
        },
    )

    assert correction_response.status_code == 200

    corrected = correction_response.json()

    assert corrected["dropout_risk_score"] == 2.0
    assert corrected["dropout_risk_level"] == "low"

    assert corrected["recommendation_headline"] == ""

    assert corrected["recommendation_tips"] == []

    assert corrected[
        "recommendation_helpful"
    ] is None

    assert corrected["feedback_text"] is None


def test_invalid_correction_is_rejected(
    client,
    account_headers,
    monkeypatch,
):
    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
    )

    checkin_id = checkin_response.json()["id"]

    empty_response = client.patch(
        (
            f"/api/checkins/"
            f"{checkin_id}/correction"
        ),
        headers=account_headers,
        json={},
    )

    assert empty_response.status_code == 422

    invalid_emotion_response = client.patch(
        (
            f"/api/checkins/"
            f"{checkin_id}/correction"
        ),
        headers=account_headers,
        json={
            "emotion_label": "excited",
        },
    )

    assert invalid_emotion_response.status_code == 422

    invalid_band_response = client.patch(
        (
            f"/api/checkins/"
            f"{checkin_id}/correction"
        ),
        headers=account_headers,
        json={
            "nutrition_category": "greasy",
        },
    )

    assert invalid_band_response.status_code == 422


def test_a_corrected_band_is_used_and_rescored(
    client,
    account_headers,
    monkeypatch,
):
    emotion_scores = {"burnout": 0.5, "fatigue": 0.5}

    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
        emotion_label="burnout",
        nutrition_category="mixed",
        emotion_scores=emotion_scores,
    )

    checkin_id = checkin_response.json()["id"]

    response = client.patch(
        f"/api/checkins/{checkin_id}/correction",
        headers=account_headers,
        json={"nutrition_category": "poor"},
    )

    assert response.status_code == 200

    corrected = response.json()

    assert corrected["corrected_nutrition_category"] == "poor"

    kept_emotion_confidences = calc_dropout_risk(
        "burnout", "poor", emotion_scores
    )
    fixed_emotion_points = calc_dropout_risk("burnout", "poor")

    assert corrected["dropout_risk_score"] == (
        kept_emotion_confidences.dropout_risk_score
    )
    assert corrected["dropout_risk_score"] != (
        fixed_emotion_points.dropout_risk_score
    )


def test_correction_is_private_between_users(
    client,
    account_headers,
    monkeypatch,
):
    checkin_response = create_test_checkin(
        client,
        account_headers,
        monkeypatch,
    )

    checkin_id = checkin_response.json()["id"]

    other_headers = register_and_accept(
        client,
        "leo@gmail.com",
    )

    response = client.patch(
        (
            f"/api/checkins/"
            f"{checkin_id}/correction"
        ),
        headers=other_headers,
        json={
            "emotion_label": "burnout",
        },
    )

    assert response.status_code == 404

def test_a_photograph_that_is_not_food_is_refused_when_read(
    client,
    account_headers,
    monkeypatch,
):

    def refuse(_path):
        raise ValueError(
            "This photograph does not seem to show food. Please take or upload another one."
        )

    monkeypatch.setattr(checkin_routes, "read_meal_photo", refuse)

    response = client.post(
        "/api/checkins/analyse-meal",
        headers=account_headers,
        files={
            "image": (
                "shoes.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 422
    assert "does not seem to show food" in response.json()["detail"]


def test_a_token_for_a_deleted_account_is_refused(
    client,
    database,
):
    registered = client.post(
        "/api/accounts/register",
        json={
            "email": "rosa@gmail.com",
            "display_name": "Rosa",
            "password": "password123",
        },
    )

    headers = {
        "Authorization": f"Bearer {registered.json()['access_token']}"
    }

    assert client.get(
        "/api/accounts/me", headers=headers
    ).status_code == 200


    database.query(Account).delete()
    database.commit()

    assert client.get(
        "/api/accounts/me", headers=headers
    ).status_code == 401


def test_meal_photograph_can_be_read_without_saving_anything(
    client,
    account_headers,
    monkeypatch,
):

    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        lambda _: {
            "food_label": "grilled salmon",
            "food_candidates": [
                {
                    "source": "dish",
                    "label": "grilled salmon",
                    "confidence": 0.72,
                    "band": "mixed",
                },
            ],
            "nutrition_category": "mixed",
        },
    )

    response = client.post(
        "/api/checkins/analyse-meal",
        headers=account_headers,
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["food_candidates"][0]["label"] == "grilled salmon"
    assert body["food_candidates"][0]["band"] == "mixed"

    listed = client.get(
        "/api/checkins", headers=account_headers
    )

    assert listed.json() == []


def test_a_confirmed_category_replaces_what_the_model_read(
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
            "scores": {"neutral": 1.0},
        },
    )
    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        lambda _: {
            "food_label": "test meal",
            "nutrition_category": "poor",
        },
    )

    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I am checking in after my workout.",
            "confirmed_nutrition_category": "balanced",
        },
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["dropout_risk_score"] == 2.0
    assert body["dropout_risk_level"] == "low"

    assert body["nutrition_category"] == "balanced"


def test_a_confirmed_category_that_is_not_a_category_is_refused(
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
            "scores": {"neutral": 1.0},
        },
    )
    monkeypatch.setattr(
        checkin_routes,
        "read_meal_photo",
        lambda _: {
            "food_label": "test meal",
            "nutrition_category": "mixed",
        },
    )

    response = client.post(
        "/api/checkins",
        headers=account_headers,
        data={
            "transcript": "I am checking in after my workout.",
            "confirmed_nutrition_category": "delicious",
        },
        files={
            "image": (
                "meal.jpg",
                b"test image",
                "image/jpeg",
            ),
        },
    )

    assert response.status_code == 400

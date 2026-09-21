# The system check runs whole check-ins through the real models from upload to advice
import os
import sys
import tempfile
import time
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# A test secret key so the check never needs the real .env file
os.environ.setdefault(
    "SECRET_KEY",
    "secret-key-1129313893183813819318931093109301038182218",
)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_database_session
from backend.app.main import app


# A real journal recording and real meal photographs from the evaluation data
AUDIO = (
    PROJECT_ROOT
    / "evaluation"
    / "data"
    / "objective2_recordings"
    / "J01.wav"
)

MEAL_IMAGE_FOLDER = (
    PROJECT_ROOT
    / "evaluation"
    / "data"
    / "objective2_photos"
    / "balanced"
)

# A pair of shoes and a drink to check that photographs without food are refused
SYSTEM_TEST_IMAGE_FOLDER = (
    PROJECT_ROOT
    / "evaluation"
    / "data"
    / "system_test_images"
)
NON_FOOD_IMAGE = SYSTEM_TEST_IMAGE_FOLDER / "shoes.jpg"
DRINK_IMAGE = SYSTEM_TEST_IMAGE_FOLDER / "drink.jpg"


passed = 0
failed = 0
timings = {}


# Record one check as passed or failed and print it
def check(name, condition, detail=""):
    global passed, failed

    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}   {detail}")


def section(title):
    print()
    print(title)
    print("-" * len(title))


# The seven parts of the system check
def main(upload_directory):
    if not AUDIO.is_file():
        raise SystemExit(f"Missing test audio: {AUDIO}")

    meal_images = sorted(MEAL_IMAGE_FOLDER.glob("*.jpeg"))

    if not meal_images:
        raise SystemExit(
            f"No meal photographs found in {MEAL_IMAGE_FOLDER}"
        )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)

    def use_test_database_session():
        database = Session()

        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_database_session] = use_test_database_session
    client = TestClient(app)

    print("AI.FIT MANUAL END-TO-END CHECK")
    print("=" * 60)
    print("Real models. The first request loads the models.")

    # Accounts, logging in and the privacy notice
    section("1. Accounts and privacy")

    check(
        "an invalid email is refused",
        client.post(
            "/api/accounts/register",
            json={
                "email": "invalid-email",
                "display_name": "Ben",
                "password": "password123",
            },
        ).status_code == 422,
    )

    check(
        "a short password is refused",
        client.post(
            "/api/accounts/register",
            json={
                "email": "ben@gmail.com",
                "display_name": "Ben",
                "password": "xyz",
            },
        ).status_code == 422,
    )

    registered = client.post(
        "/api/accounts/register",
        json={
            "email": "maya@gmail.com",
            "display_name": "Maya",
            "password": "password123",
        },
    )
    check("an account can be registered", registered.status_code == 201,
          registered.text[:120])

    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    check(
        "registering the same email twice is refused",
        client.post(
            "/api/accounts/register",
            json={
                "email": "maya@gmail.com",
                "display_name": "Maya",
                "password": "password123",
            },
        ).status_code == 409,
    )

    check(
        "login works",
        client.post(
            "/api/accounts/login",
            data={
                "username": "maya@gmail.com",
                "password": "password123",
            },
        ).status_code == 200,
    )

    check(
        "the wrong password is refused",
        client.post(
            "/api/accounts/login",
            data={
                "username": "maya@gmail.com",
                "password": "wrong-password",
            },
        ).status_code == 401,
    )

    check(
        "a check-in before accepting the privacy notice is blocked",
        client.post(
            "/api/checkins",
            headers=headers,
            data={"transcript": "I trained today and felt fine."},
            files={"image": ("m.jpg", b"x", "image/jpeg")},
        ).status_code == 403,
    )

    check(
        "the privacy notice can be accepted",
        client.post(
            "/api/accounts/privacy-notice", headers=headers
        ).status_code == 200,
    )

    check(
        "protected pages refuse a request with no token",
        client.get("/api/checkins").status_code in (401, 403),
    )

    # The real speech-to-text model
    section("2. Voice entry with the real Whisper model")

    audio_bytes = AUDIO.read_bytes()

    check(
        "an empty recording is refused",
        client.post(
            "/api/checkins/transcribe",
            headers=headers,
            files={"audio": ("v.wav", b"", "audio/wav")},
        ).status_code == 400,
    )

    check(
        "the wrong file type is refused",
        client.post(
            "/api/checkins/transcribe",
            headers=headers,
            files={"audio": ("v.txt", b"hello", "text/plain")},
        ).status_code == 400,
    )

    check(
        "a big recording is refused",
        client.post(
            "/api/checkins/transcribe",
            headers=headers,
            files={
                "audio": (
                    "v.wav",
                    b"x" * (26 * 1024 * 1024),
                    "audio/wav",
                )
            },
        ).status_code == 413,
    )

    corrupted = client.post(
        "/api/checkins/transcribe",
        headers=headers,
        files={"audio": ("v.wav", b"not really audio", "audio/wav")},
    )
    check(
        "a corrupted recording gives an error",
        corrupted.status_code >= 400,
        f"got {corrupted.status_code}",
    )

    print("Whisper is loading. It takes a while the first time")
    started = time.perf_counter()
    first = client.post(
        "/api/checkins/transcribe",
        headers=headers,
        files={"audio": ("voice.wav", audio_bytes, "audio/wav")},
    )
    timings["first transcription"] = time.perf_counter() - started

    check(
        "a real recording is transcribed",
        first.status_code == 200,
        first.text[:160],
    )

    transcript = ""

    if first.status_code == 200:
        transcript = first.json()["transcript"]
        check(
            "the transcript contains words",
            len(transcript.split()) >= 3,
            repr(transcript),
        )
        print(f"        transcript: {transcript[:90]}")

    started = time.perf_counter()
    client.post(
        "/api/checkins/transcribe",
        headers=headers,
        files={"audio": ("voice.wav", audio_bytes, "audio/wav")},
    )
    timings["later transcription"] = time.perf_counter() - started

    # The real meal models and the food check
    section("3. Meal photograph with the real SigLIP2, Kaludi and BLIP models")

    meal_bytes = meal_images[0].read_bytes()
    edited = transcript or "I trained today but felt very tired afterwards."

    check(
        "an empty photograph is refused",
        client.post(
            "/api/checkins",
            headers=headers,
            data={"transcript": edited},
            files={"image": ("m.jpg", b"", "image/jpeg")},
        ).status_code == 400,
    )

    wrong_type_response = client.post(
        "/api/checkins",
        headers=headers,
        data={"transcript": edited},
        files={"image": ("m.txt", b"hello", "text/plain")},
    )

    check(
        "a corrupted photograph is refused",
        client.post(
            "/api/checkins",
            headers=headers,
            data={"transcript": edited},
            files={"image": ("m.jpg", b"not an image", "image/jpeg")},
        ).status_code >= 400,
    )

    if NON_FOOD_IMAGE.is_file() and DRINK_IMAGE.is_file():
        non_food_response = client.post(
            "/api/checkins",
            headers=headers,
            data={"transcript": edited},
            files={
                "image": (
                    NON_FOOD_IMAGE.name,
                    NON_FOOD_IMAGE.read_bytes(),
                    "image/jpeg",
                )
            },
        )
        drink_response = client.post(
            "/api/checkins",
            headers=headers,
            data={"transcript": edited},
            files={
                "image": (
                    DRINK_IMAGE.name,
                    DRINK_IMAGE.read_bytes(),
                    "image/jpeg",
                )
            },
        )
        check(
            "Not food and drink only photographs are refused",
            wrong_type_response.status_code == 400
            and non_food_response.status_code >= 400
            and drink_response.status_code >= 400,
            f"type={wrong_type_response.status_code}, "
            f"shoes={non_food_response.status_code}, "
            f"drink={drink_response.status_code}",
        )
        if non_food_response.status_code >= 400:
            print(f"        shoes message: {non_food_response.json().get('detail')}")
        if drink_response.status_code >= 400:
            print(f"        drink message: {drink_response.json().get('detail')}")
    else:
        print(" Skip if test shoes and drink images are missing")

    # A whole check-in from transcript to advice
    section("4. A complete check-in")

    print(" Food models are loading. This takes a while the first time")
    started = time.perf_counter()
    created = client.post(
        "/api/checkins",
        headers=headers,
        data={"transcript": edited},
        files={"image": ("meal.jpg", meal_bytes, "image/jpeg")},
    )
    timings["first complete check-in"] = time.perf_counter() - started

    check(
        "the check-in is created",
        created.status_code == 201,
        created.text[:200],
    )

    if created.status_code != 201:
        print("\nStopping, the check-in could not be created.")
        summarise()
        return

    checkin = created.json()

    for field in (
        "transcript",
        "emotion_label",
        "emotion_confidence",
        "food_label",
        "nutrition_category",
        "dropout_risk_score",
        "dropout_risk_level",
    ):
        check(
            f"the result includes {field}",
            checkin.get(field) not in (None, ""),
            f"got {checkin.get(field)!r}",
        )

    print(f"        emotion : {checkin['emotion_label']} "
          f"({checkin['emotion_confidence']})")
    print(f"        food    : {checkin['food_label']}")
    print(f"        band    : {checkin['nutrition_category']}")
    print(f"        score   : {checkin['dropout_risk_score']} "
          f"-> {checkin['dropout_risk_level']}")

    score = checkin["dropout_risk_score"]
    level = checkin["dropout_risk_level"]
    signal = checkin["emotion_label"]
    band = checkin["nutrition_category"]
    expected = (
        "high" if signal in ("burnout", "low motivation")
        or (signal == "fatigue" and band == "poor")
        else "medium" if signal == "fatigue"
        else "low"
    )
    check(
        "the risk level matches the Appendix A reference grid",
        level == expected,
        f"score {score} gave {level}, expected {expected}",
    )

    check(
        "advice is given correctly",
        bool(checkin["recommendation_tips"]) == (level != "low"),
        f"level {level} with "
        f"{len(checkin['recommendation_tips'])} tips",
    )

    started = time.perf_counter()
    client.post(
        "/api/checkins",
        headers=headers,
        data={"transcript": edited},
        files={"image": ("meal.jpg", meal_bytes, "image/jpeg")},
    )
    timings["later complete check-in"] = time.perf_counter() - started

    # Correcting the signal and the meal band
    section("5. Corrections")

    target = (
        "neutral"
        if checkin["emotion_label"] in ("burnout", "low motivation")
        else "burnout"
    )

    corrected = client.patch(
        f"/api/checkins/{checkin['id']}/correction",
        headers=headers,
        json={"emotion_label": target},
    )
    check("an emotion can be corrected", corrected.status_code == 200,
          corrected.text[:120])

    if corrected.status_code == 200:
        body = corrected.json()
        check(
            "the original emotion is kept",
            body["emotion_label"] == checkin["emotion_label"],
        )
        check(
            "the corrected emotion is stored separately",
            body["corrected_emotion_label"] == target,
        )
        check(
            "the score is recalculated",
            body["dropout_risk_score"] != checkin["dropout_risk_score"],
            f"{checkin['dropout_risk_score']} -> "
            f"{body['dropout_risk_score']}",
        )
        check(
            "the risk level is recalculated",
            body["dropout_risk_level"] != checkin["dropout_risk_level"],
            f"{checkin['dropout_risk_level']} -> "
            f"{body['dropout_risk_level']}",
        )
        check(
            "the advice is rebuilt for the new level",
            bool(body["recommendation_tips"])
            == (body["dropout_risk_level"] != "low"),
        )

    check(
        "an invalid emotion is refused",
        client.patch(
            f"/api/checkins/{checkin['id']}/correction",
            headers=headers,
            json={"emotion_label": "delighted"},
        ).status_code == 422,
    )

    # Feedback, the dashboard numbers and deleting a check-in
    section("6. Feedback, dashboard and deletion")

    latest = client.get("/api/checkins", headers=headers).json()[0]

    if latest["recommendation_tips"]:
        feedback = client.post(
            f"/api/checkins/{latest['id']}/feedback",
            headers=headers,
            json={
                "helpful": True,
                "feedback_text": "  it helped  ",
            },
        )
        check("feedback can be saved", feedback.status_code == 200,
              feedback.text[:120])
        check(
            "spaces are trimmed from the feedback",
            feedback.status_code == 200
            and feedback.json()["feedback_text"] == "it helped",
        )
    else:
        print(" Skip this check-in if there is no advice to rate")

    stats = client.get("/api/checkins/stats", headers=headers).json()
    history = client.get("/api/checkins", headers=headers).json()
    trend = client.get("/api/checkins/trend", headers=headers).json()

    check(
        "the totals agree with the history",
        stats["total_checkins"] == len(history) == len(trend),
        f"{stats['total_checkins']} vs {len(history)} vs {len(trend)}",
    )
    check(
        "the history shows the newest first",
        len(history) < 2
        or history[0]["created_at"] >= history[1]["created_at"],
    )

    other = client.post(
        "/api/accounts/register",
        json={
            "email": "leo@gmail.com",
            "display_name": "Leo",
            "password": "password123",
        },
    ).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other}"}

    check(
        "another user cannot see this check-in",
        client.get("/api/checkins", headers=other_headers).json() == [],
    )
    check(
        "another user cannot correct this check-in",
        client.patch(
            f"/api/checkins/{latest['id']}/correction",
            headers=other_headers,
            json={"emotion_label": "burnout"},
        ).status_code == 404,
    )
    check(
        "another user cannot delete this check-in",
        client.delete(
            f"/api/checkins/{latest['id']}", headers=other_headers
        ).status_code == 404,
    )

    before = len(history)
    client.delete(f"/api/checkins/{latest['id']}", headers=headers)
    after = client.get("/api/checkins", headers=headers).json()
    check("a check-in can be deleted", len(after) == before - 1)

    # Nothing raw is stored and every upload is deleted
    section("7. Storage")

    columns = {
        column["name"]
        for column in inspect(engine).get_columns("checkins")
    }

    for column in (
        "corrected_emotion_label",
        "corrected_nutrition_category",
        "recommendation_headline",
        "recommendation_tips",
        "recommendation_helpful",
        "feedback_text",
    ):
        check(f"the database has {column}", column in columns)

    check(
        "no raw audio or images are stored",
        not any(
            "audio" in name or "image_data" in name
            for name in columns
        ),
        f"columns: {sorted(columns)}",
    )

    leftover = os.listdir(upload_directory)
    check(
        "no uploaded files are left in the temporary folder",
        not leftover,
        f"found {leftover[:5]}",
    )

    summarise()


# Print the timings and how many checks passed
def summarise():
    print()
    print("TIMINGS")
    print("-" * 60)

    for name, seconds in timings.items():
        print(f"  {name:28} {seconds:6.1f} s")

    print()
    print("RESULT")
    print("-" * 60)
    print(f"  passed: {passed}")
    print(f"  failed: {failed}")
    print()
    print("  ALL CHECKS PASSED" if failed == 0 else "  SOME CHECKS FAILED")


if __name__ == "__main__":
    # Save uploads in their own folder so the check can confirm they are all deleted
    with tempfile.TemporaryDirectory(prefix="aifit-system-") as upload_directory:
        upload_files = SimpleNamespace(
            mkstemp=partial(tempfile.mkstemp, dir=upload_directory)
        )
        with patch("backend.app.routers.checkin_routes.tempfile", upload_files):
            main(upload_directory)
    raise SystemExit(1 if failed else 0)

import os
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_account
from ..config import (
    ALLOWED_AUDIO_FILE_TYPES,
    ALLOWED_IMAGE_FILE_TYPES,
    settings,
)
from ..database import get_database_session
from ..db_models import Account, CheckIn
from ..logic.dropout_risk_score import MEAL_BAND_POINTS, calc_dropout_risk
from ..logic.personal_baseline import compare_with_personal_baseline
from ..logic.recommendation_rules import build_recommendations
from ..logic.transcript_check import check_transcript
from ..models.emotional_signal import detect_emotional_signal
from ..models.meal_photo import read_meal_photo
from ..models.speech_to_text import transcribe_audio
from ..schemas import (
    CheckInCorrectionRequest,
    CheckInResponse,
    DashboardStats,
    FeedbackRequest,
    MealReadingsResponse,
    RiskTrendPoint,
    TranscriptResponse,
)


router = APIRouter(
    prefix="/api/checkins",
    tags=["check-ins"],
)


# Uploads are checked for file type and size before anything reads them
def save_temp_upload(
    upload: UploadFile,
    allowed_extensions: set[str],
    max_size_mb: int,
) -> str:
    extension = Path(upload.filename or "").suffix.lower()

    # Only known file types are accepted
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This file type is not accepted - {extension}",
        )

    file_data = upload.file.read()

    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    # Audio is limited to 25 MB and images to 15 MB
    if len(file_data) > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"The file must be smaller than {max_size_mb} MB.",
        )

    # Save the upload to a temporary file so the models can read it
    file_number, temporary_path = tempfile.mkstemp(suffix=extension)

    with os.fdopen(file_number, "wb") as temporary_file:
        temporary_file.write(file_data)

    return temporary_path


# Raw uploads are deleted after analysis so they are never stored
def delete_temp_upload(file_path: str | None):
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass


# A check-in cannot be made until the user has accepted the privacy notice
def check_privacy_notice(account: Account):
    if account.privacy_notice_accepted_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please accept the privacy notice before creating a check-in.",
        )


# A user can only see and change their own check-ins
def get_owned_checkin(
    checkin_id: int,
    account: Account,
    database: Session,
) -> CheckIn:
    checkin = database.get(CheckIn, checkin_id)

    # Another user's check-in is shown as not found so its details are never given away
    if checkin is None or checkin.account_id != account.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found.",
        )

    return checkin


def get_account_checkins(
    database: Session,
    account_id: int,
    newest_first: bool = False,
) -> list[CheckIn]:
    order = CheckIn.created_at.desc() if newest_first else CheckIn.created_at.asc()

    return database.scalars(
        select(CheckIn)
        .where(CheckIn.account_id == account_id)
        .order_by(order)
    ).all()


# Get the user's previous scores and emotional signals for the baseline and the repeated signal tip
def get_prev_checkins(
    database: Session,
    account_id: int,
    exclude_checkin_id: int | None = None,
) -> tuple[list[float], list[str]]:
    # Leave out the check-in that is being corrected
    prev_checkins = [
        checkin
        for checkin in get_account_checkins(database, account_id)
        if checkin.id != exclude_checkin_id
    ]

    scores = [
        checkin.dropout_risk_score
        for checkin in prev_checkins
        if checkin.dropout_risk_score is not None
    ]

    # Use the corrected signal when the user has changed it
    emotions = [
        checkin.corrected_emotion_label or checkin.emotion_label
        for checkin in prev_checkins
    ]

    return scores, emotions


# Step 1 turns the recording into text and shows it to the user before anything is scored
@router.post("/transcribe", response_model=TranscriptResponse)
def transcribe_voice_entry(
    audio: UploadFile = File(...),
    account: Account = Depends(get_current_account),
):
    check_privacy_notice(account)

    audio_path = None

    try:
        audio_path = save_temp_upload(
            audio,
            ALLOWED_AUDIO_FILE_TYPES,
            settings.max_audio_mb,
        )

        # Whisper Base turns the recording into a transcript
        transcript = transcribe_audio(audio_path).strip()

        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No clear speech was found in the recording. Please try again.",
            )

        # Warn the user when the transcript does not mention training or feelings
        return TranscriptResponse(
            transcript=transcript,
            looks_relevant=check_transcript(transcript),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        )

    finally:
        delete_temp_upload(audio_path)


# Step 2 reads the meal photograph and sends back all three readings for the user to pick from
@router.post("/analyse-meal", response_model=MealReadingsResponse)
def analyse_meal_photo(
    image: UploadFile = File(...),
    account: Account = Depends(get_current_account),
):
    check_privacy_notice(account)

    image_path = None

    try:
        image_path = save_temp_upload(
            image,
            ALLOWED_IMAGE_FILE_TYPES,
            settings.max_image_mb,
        )

        meal_reading = read_meal_photo(image_path)

        return MealReadingsResponse(
            food_candidates=meal_reading.get("food_candidates", []),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        )

    finally:
        delete_temp_upload(image_path)


# Step 3 scores the check-in from the transcript the user checked and the band they picked
@router.post(
    "",
    response_model=CheckInResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkin(
    transcript: str = Form(...),
    image: UploadFile = File(...),
    confirmed_nutrition_category: str | None = Form(None),
    account: Account = Depends(get_current_account),
    database: Session = Depends(get_database_session),
):
    check_privacy_notice(account)

    transcript = transcript.strip()

    # Empty/very short transcripts are rejected
    if len(transcript) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The transcript is too short to analyse.",
        )

    # Very long transcripts are rejected
    if len(transcript) > 2000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The transcript must be 2000 characters or fewer.",
        )

    image_path = None

    try:
        image_path = save_temp_upload(
            image,
            ALLOWED_IMAGE_FILE_TYPES,
            settings.max_image_mb,
        )

        # DeBERTa reads the saved transcript for the emotional signals
        signal_result = detect_emotional_signal(transcript)
        meal_reading = read_meal_photo(image_path)

        chosen_meal_band = meal_reading["nutrition_category"]

        # Use the band the user picked instead of the model's first reading
        if confirmed_nutrition_category:
            confirmed_band = confirmed_nutrition_category.strip().lower()

            if confirmed_band not in MEAL_BAND_POINTS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The meal band must be balanced, mixed or poor.",
                )

            chosen_meal_band = confirmed_band

        # The dropout score is worked out first
        dropout_risk = calc_dropout_risk(
            signal_result["label"],
            chosen_meal_band,
            signal_result.get("scores"),
        )

        # Then the baseline compares the new score with the user's previous scores
        prev_scores, prev_emotional_signals = get_prev_checkins(
            database,
            account.id,
        )

        personal_baseline_result = compare_with_personal_baseline(
            dropout_risk.dropout_risk_score,
            prev_scores,
        )

        # Lastly the recommendations use the risk level, signal, meal band and risk change
        recommendation = build_recommendations(
            dropout_risk,
            personal_baseline_result,
            prev_emotional_signals,
        )

        # Save the check-in without the recording or the photograph
        checkin = CheckIn(
            account_id=account.id,
            transcript=transcript,
            emotion_label=signal_result["label"],
            emotion_confidence=signal_result["confidence"],
            emotion_confidences=signal_result.get("scores") or {},
            food_label=meal_reading["food_label"],
            nutrition_category=chosen_meal_band,
            dropout_risk_score=dropout_risk.dropout_risk_score,
            dropout_risk_level=dropout_risk.dropout_risk_level,
            recommendation_headline=recommendation["headline"],
            recommendation_tips=recommendation["tips"],
        )

        database.add(checkin)
        database.commit()
        database.refresh(checkin)

        return CheckInResponse.model_validate(checkin)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        )

    finally:
        delete_temp_upload(image_path)


# The history shows the newest check-in first
@router.get("", response_model=list[CheckInResponse])
def list_checkins(
    account: Account = Depends(get_current_account),
    database: Session = Depends(get_database_session),
):
    checkins = get_account_checkins(database, account.id, newest_first=True)

    return [CheckInResponse.model_validate(checkin) for checkin in checkins]


# The risk chart on the dashboard shows the scores in time order
@router.get("/trend", response_model=list[RiskTrendPoint])
def get_risk_trend(
    account: Account = Depends(get_current_account),
    database: Session = Depends(get_database_session),
):
    checkins = get_account_checkins(database, account.id)

    return [
        RiskTrendPoint(
            date=checkin.created_at,
            dropout_risk_score=checkin.dropout_risk_score,
            dropout_risk_level=checkin.dropout_risk_level,
        )
        for checkin in checkins
    ]


# The dashboard numbers are worked out from the user's stored check-ins
@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    account: Account = Depends(get_current_account),
    database: Session = Depends(get_database_session),
):
    checkins = get_account_checkins(database, account.id)

    scores = [checkin.dropout_risk_score for checkin in checkins]

    # Count how many check-ins were high risk
    high_risk_checkins = sum(
        checkin.dropout_risk_level == "high" for checkin in checkins
    )

    # The latest score is compared with the scores before it for the personal baseline
    if scores:
        personal_baseline_result = compare_with_personal_baseline(
            scores[-1],
            scores[:-1],
        )
        average_score = round(sum(scores) / len(scores), 2)
    else:
        personal_baseline_result = compare_with_personal_baseline(0.0, [])
        average_score = 0.0

    return DashboardStats(
        total_checkins=len(checkins),
        high_risk_checkins=high_risk_checkins,
        average_risk_score=average_score,
        personal_baseline=personal_baseline_result.baseline,
        difference_from_baseline=(
            personal_baseline_result.difference_from_baseline
        ),
        trend_direction=personal_baseline_result.risk_change_direction,
    )


# Users can rate the advice and give feedback
@router.post("/{checkin_id}/feedback", response_model=CheckInResponse)
def submit_feedback(
    checkin_id: int,
    body: FeedbackRequest,
    account: Account = Depends(get_current_account),
    database: Session = Depends(get_database_session),
):
    checkin = get_owned_checkin(checkin_id, account, database)

    # Feedback is only saved on a check-in that gave advice
    if not checkin.recommendation_tips:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only rate advice on a check-in that gave advice.",
        )

    checkin.recommendation_helpful = body.helpful
    checkin.feedback_text = (
        body.feedback_text.strip() if body.feedback_text else None
    )

    database.commit()
    database.refresh(checkin)

    return CheckInResponse.model_validate(checkin)


# Deleting a check-in removes it completely from the account
@router.delete("/{checkin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_checkin(
    checkin_id: int,
    account: Account = Depends(get_current_account),
    database: Session = Depends(get_database_session),
):
    checkin = get_owned_checkin(checkin_id, account, database)

    database.delete(checkin)
    database.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Users can correct the emotional signal or the meal band after a check-in
@router.patch("/{checkin_id}/correction", response_model=CheckInResponse)
def correct_checkin(
    checkin_id: int,
    body: CheckInCorrectionRequest,
    account: Account = Depends(get_current_account),
    database: Session = Depends(get_database_session),
):
    checkin = get_owned_checkin(checkin_id, account, database)

    if body.emotion_label is not None:
        checkin.corrected_emotion_label = body.emotion_label

    if body.nutrition_category is not None:
        checkin.corrected_nutrition_category = body.nutrition_category

    # Use the corrected values instead of the model's predicted values
    current_emotion_label = (
        checkin.corrected_emotion_label or checkin.emotion_label
    )
    current_meal_band = (
        checkin.corrected_nutrition_category or checkin.nutrition_category
    )

    # A meal only correction keeps the model's confidence scores for the emotion
    emotion_confidences = (
        None if checkin.corrected_emotion_label else checkin.emotion_confidences
    )

    # Work out the score, risk level and advice again with the same scoring function
    dropout_risk = calc_dropout_risk(
        current_emotion_label,
        current_meal_band,
        emotion_confidences,
    )

    prev_scores, prev_emotional_signals = get_prev_checkins(
        database,
        checkin.account_id,
        checkin.id,
    )

    personal_baseline_result = compare_with_personal_baseline(
        dropout_risk.dropout_risk_score,
        prev_scores,
    )

    recommendation = build_recommendations(
        dropout_risk,
        personal_baseline_result,
        prev_emotional_signals,
    )

    checkin.dropout_risk_score = dropout_risk.dropout_risk_score
    checkin.dropout_risk_level = dropout_risk.dropout_risk_level
    checkin.recommendation_headline = recommendation["headline"]
    checkin.recommendation_tips = recommendation["tips"]
    # Old feedback no longer matches the new advice so it is cleared
    checkin.recommendation_helpful = None
    checkin.feedback_text = None

    database.commit()
    database.refresh(checkin)

    return CheckInResponse.model_validate(checkin)

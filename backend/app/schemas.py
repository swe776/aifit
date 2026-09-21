from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


# What the sign up page sends to create an account
class RegisterRequest(BaseModel):
    email: EmailStr

    display_name: str = Field(
        min_length=2,
        max_length=120,
    )

    # Passwords must be at least 8 characters long
    password: str = Field(
        min_length=8,
        max_length=128,
    )

    # A name made only of spaces is refused
    @field_validator("display_name")
    @classmethod
    def validate_display_name(
        cls,
        value: str,
    ) -> str:
        display_name = value.strip()

        if len(display_name) < 2:
            raise ValueError(
                "Your name must be at least two characters long."
            )

        return display_name


# The account details sent back to the app without the password hash
class AccountResponse(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    created_at: datetime
    privacy_notice_accepted_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True
    )


# The token and account given after signing up or logging in
class LoginTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account: AccountResponse


# The transcript is sent back with a warning flag when it does not sound like a check-in
class TranscriptResponse(BaseModel):
    transcript: str

    looks_relevant: bool = True


# Everything the result screen and history show for one check-in
class CheckInResponse(BaseModel):
    id: int
    created_at: datetime

    transcript: str

    emotion_label: str
    emotion_confidence: float

    food_label: str
    nutrition_category: str

    corrected_emotion_label: str | None

    corrected_nutrition_category: str | None

    dropout_risk_score: float
    dropout_risk_level: str

    recommendation_headline: str
    recommendation_tips: list[str]

    recommendation_helpful: bool | None
    feedback_text: str | None

    model_config = ConfigDict(
        from_attributes=True
    )


# One of the three meal readings with its band or no band when the table cannot place it
class FoodReading(BaseModel):
    source: str
    label: str
    confidence: float

    band: str | None = None


# All three meal readings for the user to pick from
class MealReadingsResponse(BaseModel):
    food_candidates: list[FoodReading] = []


# Only the five signals and the three bands can be picked as a correction
class CheckInCorrectionRequest(BaseModel):
    emotion_label: Literal[
        "burnout",
        "low motivation",
        "fatigue",
        "high motivation",
        "neutral",
    ] | None = None

    nutrition_category: Literal[
        "balanced",
        "mixed",
        "poor",
    ] | None = None

    model_config = ConfigDict(
        extra="forbid"
    )

    # At least one correction has to be given
    @model_validator(mode="after")
    def validate_at_least_one_correction(
        self,
    ):
        if (
            self.emotion_label is None
            and self.nutrition_category is None
        ):
            raise ValueError(
                "Provide at least one correction."
            )

        return self


# If the advice helped and any written feedback
class FeedbackRequest(BaseModel):
    helpful: bool

    feedback_text: str | None = Field(
        default=None,
        max_length=500,
    )


# One point on the risk chart
class RiskTrendPoint(BaseModel):
    date: datetime
    dropout_risk_score: float
    dropout_risk_level: str


# The numbers shown at the top of the dashboard
class DashboardStats(BaseModel):
    total_checkins: int
    high_risk_checkins: int
    average_risk_score: float

    # The baseline is empty until there are at least two previous scores
    personal_baseline: float | None
    difference_from_baseline: float | None
    trend_direction: str

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .database import Base


# Every date is saved in UTC so check-ins stay in the right order
def current_utc_time():
    return datetime.now(timezone.utc)


# One account for each user
class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # Each email can only have one account
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(120)
    )

    # Only the Argon2 hash of the password is stored
    password_hash: Mapped[str] = mapped_column(
        String(255)
    )

    # Stays empty until the user accepts the privacy notice
    privacy_notice_accepted_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
    )

    # Deleting an account also deletes all of its check-ins
    checkins: Mapped[
        list["CheckIn"]
    ] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="CheckIn.created_at",
    )


# One saved check-in and nothing from the raw recording or photograph
class CheckIn(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        index=True,
    )

    transcript: Mapped[str] = mapped_column(
        Text
    )

    emotion_label: Mapped[str] = mapped_column(
        String(50)
    )

    emotion_confidence: Mapped[float] = mapped_column(
        Float
    )

    # The confidence score of all five signals is kept so a meal only correction can still use them
    emotion_confidences: Mapped[
        dict[str, float]
    ] = mapped_column(
        JSON,
        default=dict,
    )

    # The dish reading and the meal band the user confirmed
    food_label: Mapped[str] = mapped_column(
        String(120)
    )

    nutrition_category: Mapped[str] = mapped_column(
        String(20)
    )

    # The corrections stay empty unless the user changes the signal or the band
    corrected_emotion_label: Mapped[
        str | None
    ] = mapped_column(
        String(50),
        nullable=True,
    )

    corrected_nutrition_category: Mapped[
        str | None
    ] = mapped_column(
        String(20),
        nullable=True,
    )

    # The dropout score out of 10 and its risk level
    dropout_risk_score: Mapped[float] = mapped_column(
        Float
    )

    dropout_risk_level: Mapped[str] = mapped_column(
        String(20)
    )

    # The advice given for this check-in
    recommendation_headline: Mapped[
        str
    ] = mapped_column(
        Text
    )

    recommendation_tips: Mapped[
        list[str]
    ] = mapped_column(
        JSON
    )

    # The user's rating and feedback on the advice
    recommendation_helpful: Mapped[
        bool | None
    ] = mapped_column(
        nullable=True,
    )

    feedback_text: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    account: Mapped[
        Account
    ] = relationship(
        back_populates="checkins"
    )

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.email.enums import EmailStatus, OnboardingEmailCode


class OnboardingEmailModel(Base):
    __tablename__ = "onboarding_emails"

    onboarding_session_id: Mapped[int] = mapped_column(
        ForeignKey("onboarding_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_email: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    email_code: Mapped[OnboardingEmailCode] = mapped_column(
        Enum(OnboardingEmailCode, name="onboardingemailcode"),
        nullable=False,
        index=True,
    )
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus, name="emailstatus"),
        nullable=False,
        default=EmailStatus.SENT,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

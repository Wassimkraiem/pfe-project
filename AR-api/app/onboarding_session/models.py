from datetime import datetime
import uuid as uuid_lib

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, false, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.database import Base
from app.onboarding_session.enums import OnboardingStep


class OnboardingSessionModel(Base):
    __tablename__ = "onboarding_sessions"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid_lib.uuid4,
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    payment_email: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=True,
    )
    price_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    current_step: Mapped[OnboardingStep] = mapped_column(
        Enum(
            OnboardingStep,
            name="onboardingstep",
        ),
        default=OnboardingStep.PAGES,
        nullable=False,
    )
    payment_received: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=false(),  # type: ignore[misc]
        default=False,
    )
    last_reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reminders_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )
    requires_custom_quote: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=false(),
        default=False,
    )
    custom_quote_submitted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=false(),
        default=False,
    )
    session_details: Mapped[dict] = mapped_column("session_details", JSON, nullable=False, default={})

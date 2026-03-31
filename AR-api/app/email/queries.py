from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select, update

from app.db.database import transaction_context
from app.email.enums import EmailStatus, OnboardingEmailCode
from app.email.models import OnboardingEmailModel
from app.email.schemas import (
    AccountSetupReminderRecipientSchema,
    PrePaymentReminderRecipientSchema,
)
from app.onboarding_session.enums import OnboardingStep
from app.onboarding_session.models import OnboardingSessionModel

REMINDER_COOLDOWN_HOURS = 24
REMINDER_MAX_COUNT = 3
PRE_PAYMENT_INITIAL_DELAY_HOURS = 1
PRE_PAYMENT_MAX_WINDOW_HOURS = 72
POST_PAYMENT_DELAY_HOURS = 1


async def get_pre_payment_reminder_email_recipients(
) -> list[PrePaymentReminderRecipientSchema]:
    """
    Get recipients for pre-payment reminder email: users who started onboarding
    today, did not reach checkout (or didn't complete payment), and abandoned.
    """
    now = datetime.now(timezone.utc)
    cooldown_cutoff = now - timedelta(hours=REMINDER_COOLDOWN_HOURS)
    initial_delay_cutoff = now - timedelta(hours=PRE_PAYMENT_INITIAL_DELAY_HOURS)
    max_window_cutoff = now - timedelta(hours=PRE_PAYMENT_MAX_WINDOW_HOURS)

    async with transaction_context() as db:
        reminder_count_subq = (
            select(func.count(OnboardingEmailModel.id))
            .where(
                OnboardingEmailModel.onboarding_session_id
                == OnboardingSessionModel.id,
                OnboardingEmailModel.email_code
                == OnboardingEmailCode.PRE_PAYMENT_REMINDER,
            )
            .scalar_subquery()
        )
        last_sent_subq = (
            select(func.max(OnboardingEmailModel.sent_at))
            .where(
                OnboardingEmailModel.onboarding_session_id
                == OnboardingSessionModel.id,
                OnboardingEmailModel.email_code
                == OnboardingEmailCode.PRE_PAYMENT_REMINDER,
            )
            .scalar_subquery()
        )

        result = await db.execute(
            select(OnboardingSessionModel.email, OnboardingSessionModel.uuid).where(
                OnboardingSessionModel.payment_received.is_(False),
                OnboardingSessionModel.current_step.in_(
                    (OnboardingStep.PAGES, OnboardingStep.CHECKOUT)
                ),
                reminder_count_subq < REMINDER_MAX_COUNT,
                OnboardingSessionModel.created_at <= initial_delay_cutoff,
                OnboardingSessionModel.created_at >= max_window_cutoff,
                or_(
                    last_sent_subq.is_(None),
                    last_sent_subq <= cooldown_cutoff,
                ),
            )
        )
        rows = result.all()
        return [
            PrePaymentReminderRecipientSchema(email=row[0], session_uuid=row[1])
            for row in rows
        ]


async def get_account_setup_reminder_email_recipients(
) -> list[AccountSetupReminderRecipientSchema]:
    """
    Get recipients for account setup reminder email:
    users who paid, are in ACCOUNT step, and haven't completed onboarding.
    """
    now = datetime.now(timezone.utc)
    delay_cutoff = now - timedelta(hours=POST_PAYMENT_DELAY_HOURS)

    async with transaction_context() as db:
        reminder_count_subq = (
            select(func.count(OnboardingEmailModel.id))
            .where(
                OnboardingEmailModel.onboarding_session_id
                == OnboardingSessionModel.id,
                OnboardingEmailModel.email_code
                == OnboardingEmailCode.ACCOUNT_SETUP_REMINDER,
            )
            .scalar_subquery()
        )

        result = await db.execute(
            select(
                OnboardingSessionModel.email,
                OnboardingSessionModel.uuid,
                OnboardingSessionModel.session_details,
            ).where(
                OnboardingSessionModel.payment_received.is_(True),
                OnboardingSessionModel.current_step == OnboardingStep.ACCOUNT,
                reminder_count_subq < 1,
            )
        )
        rows = result.all()
        recipients: list[AccountSetupReminderRecipientSchema] = []
        for row in rows:
            session_details = row[2] or {}
            checkout = session_details.get("checkout") or {}
            payment_completed_at = checkout.get("payment_completed_at")
            if not payment_completed_at:
                continue
            try:
                payment_dt = datetime.fromisoformat(
                    str(payment_completed_at).replace("Z", "+00:00")
                )
                if payment_dt.tzinfo is None:
                    payment_dt = payment_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if payment_dt <= delay_cutoff:
                recipients.append(
                    AccountSetupReminderRecipientSchema(
                        email=row[0], session_uuid=row[1]
                    )
                )
        return recipients


async def has_payment_confirmation_been_sent(session_uuid: UUID) -> bool:
    """Return True if a PAYMENT_CONFIRMATION email was already recorded for this session."""
    async with transaction_context() as db:
        result = await db.execute(
            select(OnboardingEmailModel.id)
            .join(
                OnboardingSessionModel,
                OnboardingEmailModel.onboarding_session_id == OnboardingSessionModel.id,
            )
            .where(
                OnboardingSessionModel.uuid == session_uuid,
                OnboardingEmailModel.email_code == OnboardingEmailCode.PAYMENT_CONFIRMATION,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None


async def record_onboarding_email_sent(
    session_uuid: UUID,
    recipient_email: str,
    email_code: OnboardingEmailCode,
    status: EmailStatus = EmailStatus.SENT,
    metadata: dict | None = None,
) -> None:
    """Record a sent onboarding email and update reminder stats if applicable."""
    now = datetime.now(timezone.utc)
    async with transaction_context() as db:
        result = await db.execute(
            select(OnboardingSessionModel.id).where(
                OnboardingSessionModel.uuid == session_uuid
            )
        )
        session_id = result.scalar_one_or_none()
        if not session_id:
            return

        db.add(
            OnboardingEmailModel(
                onboarding_session_id=session_id,
                recipient_email=recipient_email,
                email_code=email_code,
                status=status,
                sent_at=now,
                metadata_=metadata,
            )
        )

        if email_code in (
            OnboardingEmailCode.PRE_PAYMENT_REMINDER,
            OnboardingEmailCode.ACCOUNT_SETUP_REMINDER,
        ):
            await db.execute(
                update(OnboardingSessionModel)
                .where(OnboardingSessionModel.uuid == session_uuid)
                .values(
                    last_reminder_sent_at=now,
                    reminders_count=OnboardingSessionModel.reminders_count + 1,
                )
            )

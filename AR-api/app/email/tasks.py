"""Celery tasks for asynchronous email delivery."""

import asyncio
import logging
import uuid

from app.celery_app import celery_app
from app.db.database import async_engine
from app.email.enums import EmailStatus, OnboardingEmailCode
from app.email.queries import has_payment_confirmation_been_sent, record_onboarding_email_sent
from app.email.services import get_email_service

logger = logging.getLogger(__name__)


@celery_app.task(
    name="email.send_setup_account_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_setup_account_email_task(
    recipient_email: str,
    first_name: str,
    complete_account_link: str,
    recipient_name: str | None = None,
    session_uuid: str | None = None,
    email_code: str | None = None,
) -> None:
    """Queue task to send setup-account email."""
    email_service = get_email_service()
    code_enum: OnboardingEmailCode | None = None
    if email_code:
        try:
            code_enum = OnboardingEmailCode(email_code)
        except ValueError:
            logger.warning("Unknown onboarding email_code: %s", email_code)

    async def _run() -> None:
        await async_engine.dispose()
        try:
            await email_service.send_setup_account_email(
                recipient_email=recipient_email,
                first_name=first_name,
                complete_account_link=complete_account_link,
                recipient_name=recipient_name,
                email_code=code_enum,
            )
            if session_uuid and code_enum:
                try:
                    await record_onboarding_email_sent(
                        session_uuid=uuid.UUID(session_uuid),
                        recipient_email=recipient_email,
                        email_code=code_enum,
                        status=EmailStatus.SENT,
                    )
                except Exception:
                    logger.exception(
                        "Failed to record onboarding email %s for session %s",
                        email_code,
                        session_uuid,
                    )
        finally:
            await async_engine.dispose()

    asyncio.run(_run())


@celery_app.task(
    name="email.send_payment_success_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_payment_success_email_task(
    recipient_email: str,
    first_name: str,
    complete_account_link: str,
    recipient_name: str | None = None,
    session_uuid: str | None = None,
    channels: list[str] | None = None,
    amount_display: str = "",
    plan_label: str = "",
    signature: str | None = None,
    signed_at: str | None = None,
) -> None:
    """Queue task to send payment success confirmation email with PDF attachment."""
    if not session_uuid:
        logger.warning(
            "send_payment_success_email_task called without session_uuid for %s — skipping.",
            recipient_email,
        )
        return

    email_service = get_email_service()
    session_id = uuid.UUID(session_uuid)

    async def _run() -> None:
        # Dispose stale engine connections from any previous event loop so all
        # DB operations below run cleanly inside this single event loop.
        await async_engine.dispose()
        try:
            # Idempotency guard — check BEFORE sending so Stripe retries are safe.
            already_sent = await has_payment_confirmation_been_sent(session_id)
            if already_sent:
                logger.info(
                    "Payment confirmation already sent for session %s — skipping.",
                    session_uuid,
                )
                return

            await email_service.send_payment_success_email(
                recipient_email=recipient_email,
                first_name=first_name,
                complete_account_link=complete_account_link,
                recipient_name=recipient_name,
                channels=channels or [],
                amount_display=amount_display,
                plan_label=plan_label,
                signature=signature,
                signed_at=signed_at,
            )

            # Record AFTER a successful send so the idempotency check blocks retries.
            await record_onboarding_email_sent(
                session_uuid=session_id,
                recipient_email=recipient_email,
                email_code=OnboardingEmailCode.PAYMENT_CONFIRMATION,
                status=EmailStatus.SENT,
            )
        finally:
            await async_engine.dispose()

    asyncio.run(_run())


@celery_app.task(
    name="email.send_payment_issue_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_payment_issue_email_task(
    recipient_email: str,
    first_name: str,
    recipient_name: str | None = None,
) -> None:
    """Queue task to send payment processing issue email."""
    email_service = get_email_service()
    asyncio.run(
        email_service.send_payment_issue_email(
            recipient_email=recipient_email,
            first_name=first_name,
            recipient_name=recipient_name,
        )
    )


@celery_app.task(
    name="email.send_welcome_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_welcome_email_task(
    recipient_email: str,
    first_name: str,
    recipient_name: str | None = None,
    assignee_link: str | None = None,
) -> None:
    """Queue task to send welcome email."""
    email_service = get_email_service()
    asyncio.run(
        email_service.send_welcome_email(
            recipient_email=recipient_email,
            first_name=first_name,
            recipient_name=recipient_name,
            assignee_link=assignee_link,
        )
    )


@celery_app.task(
    name="email.send_custom_quote_created_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_custom_quote_created_email_task(
    recipient_email: str,
    first_name: str,
    recipient_name: str | None = None,
    session_uuid: str | None = None,
) -> None:
    """Queue task to send custom quote created email."""
    email_service = get_email_service()

    async def _run() -> None:
        await async_engine.dispose()
        try:
            await email_service.send_custom_quote_created_email(
                recipient_email=recipient_email,
                first_name=first_name,
                recipient_name=recipient_name,
            )
            if session_uuid:
                try:
                    await record_onboarding_email_sent(
                        session_uuid=uuid.UUID(session_uuid),
                        recipient_email=recipient_email,
                        email_code=OnboardingEmailCode.CUSTOM_QUOTE_REQUEST,
                        status=EmailStatus.SENT,
                    )
                except Exception:
                    logger.exception(
                        "Failed to record onboarding email %s for session %s",
                        OnboardingEmailCode.CUSTOM_QUOTE_REQUEST.value,
                        session_uuid,
                    )
        finally:
            await async_engine.dispose()

    asyncio.run(_run())


@celery_app.task(
    name="email.send_custom_quote_team_notification_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_custom_quote_team_notification_email_task(
    submitter_email: str,
    channels: list[str],
    triggers: list[dict],
) -> None:
    """Queue task to send custom quote team notification email."""
    email_service = get_email_service()
    asyncio.run(
        email_service.send_custom_quote_team_notification_email(
            submitter_email=submitter_email,
            channels=channels,
            triggers=triggers,
        )
    )


@celery_app.task(
    name="email.send_custom_quote_price_submitted_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_custom_quote_price_submitted_email_task(
    recipient_email: str,
    first_name: str,
    finish_link: str,
    recipient_name: str | None = None,
    session_uuid: str | None = None,
) -> None:
    """Queue task to send custom quote price submitted notification email."""
    email_service = get_email_service()

    async def _run() -> None:
        await async_engine.dispose()
        try:
            await email_service.send_custom_quote_price_submitted_email(
                recipient_email=recipient_email,
                first_name=first_name,
                finish_link=finish_link,
                recipient_name=recipient_name,
            )
            if session_uuid:
                try:
                    await record_onboarding_email_sent(
                        session_uuid=uuid.UUID(session_uuid),
                        recipient_email=recipient_email,
                        email_code=OnboardingEmailCode.CUSTOM_QUOTE_PRICE_SUBMITTED,
                        status=EmailStatus.SENT,
                    )
                except Exception:
                    logger.exception(
                        "Failed to record onboarding email CUSTOM_QUOTE_PRICE_SUBMITTED for session %s",
                        session_uuid,
                    )
        finally:
            await async_engine.dispose()

    asyncio.run(_run())

"""Celery tasks for asynchronous Stripe webhook processing."""

import asyncio
import json
import logging
import math
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any, TypeVar
from urllib.parse import urlparse

from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import select
from sqlalchemy.exc import DisconnectionError, OperationalError

from app.celery_app import celery_app
from app.canto.tasks import (
    add_user_to_basic_group_task,
    remove_user_from_basic_group_task,
)
from app.core.config import settings
from app.db.database import transaction_context
from app.email.tasks import send_payment_success_email_task
from app.onboarding_session.exceptions import OnboardingSessionNotFound
from app.onboarding_session.services import OnboardingSessionService
from app.payment.services import PaymentService
from app.slack.tasks import (
    send_slack_subscription_announcement_task,
    send_slack_whitelist_notification_task,
)
from app.user.models import UserModel

logger = logging.getLogger(__name__)
T = TypeVar("T")

_worker_event_loop: asyncio.AbstractEventLoop | None = None


def _get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """Return a process-local asyncio loop reused across Celery tasks."""
    global _worker_event_loop

    if _worker_event_loop is None or _worker_event_loop.is_closed():
        _worker_event_loop = asyncio.new_event_loop()
    return _worker_event_loop


def _run_in_worker_loop(coro: Coroutine[Any, Any, T]) -> T:
    """Run async code on a stable event loop per worker process."""
    loop = _get_worker_event_loop()
    return loop.run_until_complete(coro)

_PAYMENT_EVENTS = frozenset(
    {"checkout.session.completed", "invoice.payment_succeeded", "invoice.payment_failed"}
)

# Timing race: Stripe can fire webhooks before the session is committed.
# Retry with a fixed delay to give the session time to appear.
_SESSION_NOT_FOUND_RETRY_COUNTDOWN_SECONDS = 30
_SESSION_NOT_FOUND_MAX_RETRIES = 5


class _SessionNotFoundRetry(Exception):
    """Raised internally to trigger a fixed-delay retry for session timing races."""


@celery_app.task(
    name="payment.process_stripe_webhook",
    bind=True,
    # Retry automatically on transient network and DB connectivity failures.
    # _SessionNotFoundRetry is handled manually below with a fixed countdown.
    autoretry_for=(
        ConnectionError,
        TimeoutError,
        OSError,
        OperationalError,       # SQLAlchemy: DB connection dropped or query failed
        DisconnectionError,     # SQLAlchemy: pool connection lost mid-request
    ),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 10},
    # acks_late=True: the broker keeps the message until the task returns
    # successfully. A crashed or OOM-killed worker causes a re-queue, not
    # silent data loss.
    acks_late=True,
    # reject_on_worker_lost: emit NACK so the broker re-queues the message
    # when the worker process disappears unexpectedly.
    reject_on_worker_lost=True,
)
def process_stripe_webhook_task(self, event: dict) -> None:
    """Process a Stripe webhook event asynchronously.

    Enqueued immediately after signature verification so the webhook endpoint
    returns 200 to Stripe in milliseconds. All DB writes, emails, and Slack
    notifications run here with retries that guarantee payment data is never lost.
    """
    event_id = event.get("id", "unknown")
    event_type = event.get("type", "unknown")

    try:
        _run_in_worker_loop(_run(event))

    except _SessionNotFoundRetry as exc:
        # Timing race — session not committed yet. Wait, then retry.
        logger.warning(
            "Onboarding session not found for webhook, scheduling retry: "
            "event_id=%s event_type=%s attempt=%s/%s",
            event_id,
            event_type,
            self.request.retries + 1,
            _SESSION_NOT_FOUND_MAX_RETRIES,
        )
        try:
            raise self.retry(
                exc=exc,
                countdown=_SESSION_NOT_FOUND_RETRY_COUNTDOWN_SECONDS,
                max_retries=_SESSION_NOT_FOUND_MAX_RETRIES,
            )
        except MaxRetriesExceededError:
            _log_unrecoverable(event, event_id, event_type, _SESSION_NOT_FOUND_MAX_RETRIES)
            raise

    except MaxRetriesExceededError:
        # autoretry_for exhausted all 10 attempts.
        _log_unrecoverable(event, event_id, event_type, self.max_retries or 0)
        raise

    except Exception as exc:
        retries_used = self.request.retries
        max_retries = self.max_retries or 0
        logger.error(
            "payment.process_stripe_webhook failed (attempt %s/%s): "
            "event_id=%s event_type=%s exc=%s",
            retries_used + 1,
            max_retries,
            event_id,
            event_type,
            exc,
        )
        raise


def _log_unrecoverable(event: dict, event_id: str, event_type: str, max_retries: int) -> None:
    """Emit a CRITICAL log with the full payload when all retries are exhausted.

    Search CloudWatch for 'PAYMENT_WEBHOOK_UNRECOVERABLE' to find events that
    need manual replay via the Stripe dashboard → Webhooks → Resend.
    """
    logger.critical(
        "PAYMENT_WEBHOOK_UNRECOVERABLE: all %s retries exhausted, manual replay required. "
        "event_id=%s event_type=%s payload=%s",
        max_retries,
        event_id,
        event_type,
        json.dumps(event),
    )


async def _run(event: dict) -> None:
    await _handle_payment_event(event)


async def _handle_payment_event(event: dict) -> None:
    event_name = event.get("type", "unknown")
    event_id = event.get("id", "unknown")

    if event_name not in _PAYMENT_EVENTS:
        logger.info("Skipping unhandled event type in task: %s", event_name)
        return

    event_object = event.get("data", {}).get("object", {})
    metadata = event_object.get("metadata") or {}
    billing_reason = event_object.get("billing_reason")
    user_email = (
        event_object.get("customer_email")
        or (event_object.get("customer_details") or {}).get("email")
        or event_object.get("user_email")
    )

    logger.info(
        "Processing payment webhook: type=%s id=%s email=%s billing_reason=%s",
        event_name,
        event_id,
        user_email,
        billing_reason,
    )

    if event_name == "invoice.payment_failed" and billing_reason == "subscription_cycle":
        await _handle_renewal_failure(event_object=event_object, user_email=user_email)
        return

    if event_name == "invoice.payment_succeeded" and billing_reason == "subscription_cycle":
        await _handle_renewal_success(event_object=event_object, user_email=user_email)
        return

    if event_name == "invoice.payment_succeeded" and billing_reason == "subscription_create":
        logger.info(
            "Ignoring invoice.payment_succeeded subscription_create to avoid checkout race: id=%s",
            event_id,
        )
        return

    if event_name == "invoice.payment_failed":
        logger.info(
            "Ignoring invoice.payment_failed with billing_reason=%s id=%s",
            billing_reason,
            event_id,
        )
        return

    # ------------------------------------------------------------------ #
    # Phase 1 — Persist payment data.                                      #
    # Commit completes before any notification is dispatched so the DB     #
    # record is safe even if Phase 2 fails or the worker is interrupted.   #
    # ------------------------------------------------------------------ #
    updated_session = await _persist_payment(
        event_object=event_object,
        metadata=metadata,
        event_name=event_name,
        event_id=event_id,
    )

    logger.info(
        "Payment data committed: session_id=%s email=%s event_id=%s",
        updated_session.id,
        user_email,
        event_id,
    )

    # ------------------------------------------------------------------ #
    # Phase 2 — Notifications (best-effort).                               #
    # Payment is already persisted; downstream tasks carry their own       #
    # retry logic and idempotency guards.                                  #
    # ------------------------------------------------------------------ #
    if event_name == "checkout.session.completed":
        _dispatch_checkout_notifications(
            updated_session=updated_session,
            user_email=user_email,
        )
    else:
        logger.info(
            "Skipping confirmation email for %s — "
            "only checkout.session.completed triggers the confirmation.",
            event_name,
        )


def _extract_invoice_fields(event_object: dict) -> dict[str, str | int]:
    invoice_id = str(event_object.get("id") or "")
    subscription_id = str(event_object.get("subscription") or "")
    customer_id = str(event_object.get("customer") or "")
    amount = int(event_object.get("amount_paid") or event_object.get("amount_due") or 0)
    currency = str(event_object.get("currency") or "USD").upper()
    return {
        "invoice_id": invoice_id,
        "subscription_id": subscription_id,
        "customer_id": customer_id,
        "amount": amount,
        "currency": currency,
    }


async def _handle_renewal_failure(*, event_object: dict, user_email: str | None) -> None:
    fields = _extract_invoice_fields(event_object)
    invoice_id = str(fields["invoice_id"])
    if not invoice_id:
        logger.warning("Skipping renewal failure without invoice id: email=%s", user_email)
        return

    async with transaction_context() as db:
        payment_service = PaymentService(db=db)
        user = await payment_service.find_user_for_renewal_event(
            subscription_id=str(fields["subscription_id"]),
            customer_id=str(fields["customer_id"]),
            user_email=user_email,
        )
        if not user:
            logger.warning(
                "No user found for renewal failure: invoice_id=%s subscription_id=%s customer_id=%s email=%s",
                invoice_id,
                fields["subscription_id"],
                fields["customer_id"],
                user_email,
            )
            return

        grace_ends_at, first_failure = await payment_service.mark_renewal_failed(
            user=user,
            invoice_id=invoice_id,
            subscription_id=str(fields["subscription_id"]) or None,
            customer_id=str(fields["customer_id"]) or None,
            amount=int(fields["amount"]),
            currency=str(fields["currency"]),
            metadata=event_object,
        )
        user_id = user.id

    if first_failure:
        now = datetime.now(UTC)
        countdown_seconds = max(0, math.ceil((grace_ends_at - now).total_seconds()))
        enforce_renewal_grace_expired_task.apply_async(
            kwargs={"user_id": user_id},
            countdown=countdown_seconds,
        )
        logger.info(
            "Scheduled renewal grace enforcement for user_id=%s in %s seconds",
            user_id,
            countdown_seconds,
        )
    else:
        logger.info(
            "Renewal failure already active; grace not reset. user_id=%s",
            user_id,
        )


async def _handle_renewal_success(*, event_object: dict, user_email: str | None) -> None:
    fields = _extract_invoice_fields(event_object)
    invoice_id = str(fields["invoice_id"])
    if not invoice_id:
        logger.warning("Skipping renewal success without invoice id: email=%s", user_email)
        return

    async with transaction_context() as db:
        payment_service = PaymentService(db=db)
        user = await payment_service.find_user_for_renewal_event(
            subscription_id=str(fields["subscription_id"]),
            customer_id=str(fields["customer_id"]),
            user_email=user_email,
        )
        if not user:
            logger.warning(
                "No user found for renewal success: invoice_id=%s subscription_id=%s customer_id=%s email=%s",
                invoice_id,
                fields["subscription_id"],
                fields["customer_id"],
                user_email,
            )
            return

        was_suspended = await payment_service.mark_renewal_paid(
            user=user,
            invoice_id=invoice_id,
            subscription_id=str(fields["subscription_id"]) or None,
            customer_id=str(fields["customer_id"]) or None,
            amount=int(fields["amount"]),
            currency=str(fields["currency"]),
            metadata=event_object,
        )
        user_email_to_restore = user.email

    if was_suspended:
        if not settings.canto_enabled:
            logger.info(
                "Renewal recovered; Canto disabled (ENV=%s), skipping access restore for %s",
                settings.ENV,
                user_email_to_restore,
            )
            return

        restore_task = add_user_to_basic_group_task.delay(user_email=user_email_to_restore)
        logger.info(
            "Renewal recovered; enqueued Canto access restore for %s task_id=%s",
            user_email_to_restore,
            restore_task.id,
        )
    else:
        logger.info("Renewal success processed without active suspension: %s", user_email_to_restore)


async def _persist_payment(
    *,
    event_object: dict,
    metadata: dict,
    event_name: str,
    event_id: str,
) -> object:
    """Write payment data to the DB and return the updated session.

    Raises _SessionNotFoundRetry (instead of OnboardingSessionNotFound) so
    the task layer can apply a fixed retry delay for timing races.
    """
    onboarding_session_uuid = metadata.get("onboarding_session_uuid")
    checkout_signature = metadata.get("signature")

    try:
        async with transaction_context() as db:
            service = OnboardingSessionService(db=db)
            return await service.mark_payment_received(
                webhook_data=event_object,
                onboarding_session_uuid=onboarding_session_uuid,
                signature=checkout_signature,
                custom_data=metadata,
            )
    except OnboardingSessionNotFound as exc:
        raise _SessionNotFoundRetry(str(exc)) from exc


def _dispatch_checkout_notifications(*, updated_session, user_email: str | None) -> None:
    """Enqueue email and Slack notifications for a completed checkout.

    Runs after the DB commit.  Failures are logged but do not affect the
    persisted payment record.
    """
    session_details = updated_session.session_details or {}
    recipient_email = user_email or updated_session.email

    account = session_details.get("account")
    account = account if isinstance(account, dict) else {}
    first_name = (
        account.get("first_name")
        or recipient_email.split("@")[0].split(".")[0].capitalize()
        or "there"
    )
    last_name = account.get("last_name") or ""

    parsed = urlparse(settings.FRONTEND_URL)
    complete_account_link = (
        f"{parsed.scheme}://{parsed.netloc}/signup/?session_id={updated_session.uuid}"
    )

    checkout_data = session_details.get("checkout") or {}
    pages_data = session_details.get("pages") or {}
    channels: list[str] = pages_data.get("channels") or []
    if not isinstance(channels, list):
        channels = []

    amount_cents = int(checkout_data.get("amount") or 0)
    currency = str(checkout_data.get("currency") or "USD").upper()
    amount_display = f"${amount_cents / 100:,.2f} {currency}"
    plan_label = PaymentService._resolve_plan_from_interval_or_id(
        interval=None,
        price_id=str(checkout_data.get("price_id") or ""),
    ).capitalize()

    signed_at = checkout_data.get("service_agreement_signed_at") or ""

    try:
        send_payment_success_email_task.delay(
            recipient_email=recipient_email,
            first_name=first_name,
            complete_account_link=complete_account_link,
            session_uuid=str(updated_session.uuid),
            channels=channels,
            amount_display=amount_display,
            plan_label=plan_label,
            signature=checkout_data.get("signature"),
            signed_at=signed_at,
        )
        if settings.slack_whitelisted_enabled:
            send_slack_whitelist_notification_task.delay(channels=channels)
        if settings.slack_enabled:
            send_slack_subscription_announcement_task.delay(
                email=recipient_email,
                first_name=first_name,
                last_name=last_name,
                amount=amount_display,
                plan=plan_label,
                signed_at=signed_at,
            )
    except Exception:
        logger.exception(
            "Failed to enqueue payment notifications for %s (payment already saved)",
            recipient_email,
        )


@celery_app.task(
    name="payment.enforce_renewal_grace_expired",
    bind=True,
    autoretry_for=(
        ConnectionError,
        TimeoutError,
        OSError,
        OperationalError,
        DisconnectionError,
    ),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 10},
    acks_late=True,
    reject_on_worker_lost=True,
)
def enforce_renewal_grace_expired_task(self, user_id: int) -> None:
    """Suspend Canto access when renewal grace period expires."""
    try:
        _run_in_worker_loop(_enforce_renewal_grace_expired(user_id=user_id))
    except Exception as exc:
        logger.error(
            "payment.enforce_renewal_grace_expired failed: user_id=%s retries=%s exc=%s",
            user_id,
            self.request.retries,
            exc,
        )
        raise


async def _enforce_renewal_grace_expired(*, user_id: int) -> None:
    async with transaction_context() as db:
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_id).limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("Grace enforcement skipped: user not found id=%s", user_id)
            return

        if user.renewal_failed_at is None or user.renewal_grace_ends_at is None:
            logger.info(
                "Grace enforcement no-op (no active renewal failure): user_id=%s",
                user_id,
            )
            return

        if user.canto_access_suspended:
            logger.info("Grace enforcement no-op (already suspended): user_id=%s", user_id)
            return

        if datetime.now(UTC) < user.renewal_grace_ends_at:
            logger.info(
                "Grace enforcement no-op (deadline not reached): user_id=%s deadline=%s",
                user_id,
                user.renewal_grace_ends_at,
            )
            return

        user.canto_access_suspended = True
        await db.flush()
        suspended_email = user.email

    if not settings.canto_enabled:
        logger.info(
            "Renewal grace expired; Canto disabled (ENV=%s), suspended in DB only for user_id=%s email=%s",
            settings.ENV,
            user_id,
            suspended_email,
        )
        return

    suspend_task = remove_user_from_basic_group_task.delay(user_email=suspended_email)
    logger.info(
        "Renewal grace expired; enqueued Canto suspension for user_id=%s email=%s task_id=%s",
        user_id,
        suspended_email,
        suspend_task.id,
    )

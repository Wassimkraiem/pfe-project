import logging

from fastapi import APIRouter, Request

from app.core.config import settings
from app.payment.exceptions import InvalidWebhookSignature
from app.payment.services import parse_webhook_event
from app.payment.tasks import process_stripe_webhook_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["webhooks"])


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Receive and verify a Stripe webhook event, then hand off to Celery.

    Signature verification is the only work done here so Stripe always receives
    a 200 within milliseconds — well inside its 30-second delivery timeout.
    All business logic (DB updates, emails, Slack) runs in process_stripe_webhook_task.
    """
    body = await request.body()

    signature = request.headers.get("Stripe-Signature")

    if not signature and settings.ENV != "local":
        logger.warning("Webhook rejected: missing Stripe-Signature header")
        raise InvalidWebhookSignature()

    try:
        event = parse_webhook_event(
            payload=body,
            signature=signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception as exc:
        logger.warning("Webhook signature verification failed")
        raise InvalidWebhookSignature() from exc

    event_name = event.get("type", "unknown")
    event_id = event.get("id", "unknown")
    logger.info(
        "Webhook verified, enqueuing for async processing: type=%s id=%s",
        event_name,
        event_id,
    )

    process_stripe_webhook_task.delay(event)

    return {"status": "received", "event": event_name}

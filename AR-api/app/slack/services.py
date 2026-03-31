"""Slack webhook notification service."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 10


async def _send_to_webhook(webhook_url: str, text: str, blocks: list[dict] | None = None) -> bool:
    """Send a message to a specific Slack webhook URL.

    Args:
        webhook_url: The Slack webhook URL to send to.
        text: Fallback text for the message (shown in notifications).
        blocks: Optional Slack Block Kit blocks for rich formatting.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    payload: dict = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(webhook_url, json=payload)
            if response.is_success:
                logger.info("Slack webhook message sent successfully")
                return True
            logger.warning(
                "Slack webhook returned non-success status: %s %s",
                response.status_code,
                response.text,
            )
            return False
    except httpx.TimeoutException:
        logger.warning("Slack webhook request timed out")
        return False
    except httpx.RequestError as exc:
        logger.warning("Slack webhook request failed: %s", exc)
        return False


async def send_webhook_message(text: str, blocks: list[dict] | None = None) -> bool:
    """Send a message to the default Slack webhook.

    Args:
        text: Fallback text for the message (shown in notifications).
        blocks: Optional Slack Block Kit blocks for rich formatting.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    if not settings.slack_enabled:
        logger.debug("Slack notifications disabled, skipping webhook message")
        return False

    return await _send_to_webhook(settings.SLACK_WEBHOOK_URL, text, blocks)


async def send_whitelisted_webhook_message(text: str, blocks: list[dict] | None = None) -> bool:
    """Send a message to the whitelisted/subscriptions-onboarding Slack webhook.

    Args:
        text: Fallback text for the message (shown in notifications).
        blocks: Optional Slack Block Kit blocks for rich formatting.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    if not settings.slack_whitelisted_enabled:
        logger.debug("Slack whitelisted notifications disabled, skipping webhook message")
        return False

    return await _send_to_webhook(settings.SLACK_WEBHOOK_URL_WHITELISTED, text, blocks)

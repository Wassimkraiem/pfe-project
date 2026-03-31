"""Celery tasks for Slack notifications."""

import asyncio

from app.celery_app import celery_app
from app.core.config import settings
from app.slack.services import send_webhook_message, send_whitelisted_webhook_message


def _format_quote_message(email: str, channels: list[str], triggers: list[dict]) -> tuple[str, list[dict]]:
    """Format the custom quote notification message."""
    channel_count = len(channels)
    channel_list = "\n".join(f"• {ch}" for ch in channels[:10])
    if len(channels) > 10:
        channel_list += f"\n• ... and {len(channels) - 10} more"

    trigger_flags = list({t.get("flag", "UNKNOWN") for t in triggers if isinstance(t, dict)})
    trigger_text = ", ".join(trigger_flags) if trigger_flags else "N/A"

    text = f"New Custom Quote Request from {email}"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "New Custom Quote Request", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Email:*\n{email}"},
                {"type": "mrkdwn", "text": f"*Channels:*\n{channel_count} channel(s)"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Channel URLs:*\n{channel_list}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Triggers:*\n{trigger_text}"},
        },
    ]

    return text, blocks


def _format_payment_message(email: str, amount: str, plan: str, channels: list[str]) -> tuple[str, list[dict]]:
    """Format the payment notification message."""
    channel_count = len(channels)

    text = f"Payment Received from {email}"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Payment Received", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Email:*\n{email}"},
                {"type": "mrkdwn", "text": f"*Plan:*\n{plan} - {amount}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Channels:*\n{channel_count} channel(s) whitelisted"},
        },
    ]

    return text, blocks


def _format_whitelist_message(channels: list[str]) -> tuple[str, list[dict]]:
    """Format the whitelist channels notification message."""
    channel_list = "\n".join(f"• {ch}" for ch in channels)

    text = "New Content Subscription, please whitelist & record these channels"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "New Content Subscription", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Please whitelist & record these channels:*",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": channel_list},
        },
    ]

    return text, blocks


def _format_subscription_announcement(
    email: str,
    first_name: str,
    last_name: str,
    amount: str,
    plan: str,
    signed_at: str,
) -> tuple[str, list[dict]]:
    """Format the subscription announcement for subscriptions-onboarding channel."""
    term = "1-year (paid per month)" if plan.lower() == "monthly" else "1-year (paid yearly)"

    text = f"New content subscription from {first_name} {last_name}!"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":man_dancing::skin-tone-3: :tada: *Ladies and Gentlemen, It's Time to celebrate!*\n*We have a new content subscription!*",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Rate (per month):*\n{amount}"},
                {"type": "mrkdwn", "text": f"*Term (auto renews):*\n{term}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Date Signed:*\n{signed_at}"},
                {"type": "mrkdwn", "text": f"*First Name:*\n{first_name}"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Last Name:*\n{last_name}"},
                {"type": "mrkdwn", "text": f"*Email:*\n{email}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Checkout & Managed Through Stripe for auto-billing._",
                },
            ],
        },
    ]

    return text, blocks


@celery_app.task(
    name="slack.send_quote_notification",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_slack_quote_notification_task(
    email: str,
    channels: list[str],
    triggers: list[dict],
) -> None:
    """Notify Slack when a custom quote is submitted."""
    if not settings.slack_enabled:
        return

    text, blocks = _format_quote_message(email, channels, triggers)
    asyncio.run(send_webhook_message(text=text, blocks=blocks))



@celery_app.task(
    name="slack.send_whitelist_notification",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_slack_whitelist_notification_task(channels: list[str]) -> None:
    """Notify Slack (whitelisted channel) with channels to whitelist after payment."""
    if not settings.slack_whitelisted_enabled:
        return

    text, blocks = _format_whitelist_message(channels)
    asyncio.run(send_whitelisted_webhook_message(text=text, blocks=blocks))


@celery_app.task(
    name="slack.send_subscription_announcement",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_slack_subscription_announcement_task(
    email: str,
    first_name: str,
    last_name: str,
    amount: str,
    plan: str,
    signed_at: str,
) -> None:
    """Send subscription celebration announcement to Slack."""
    if not settings.slack_enabled:
        return

    text, blocks = _format_subscription_announcement(
        email=email,
        first_name=first_name,
        last_name=last_name,
        amount=amount,
        plan=plan,
        signed_at=signed_at,
    )
    asyncio.run(send_webhook_message(text=text, blocks=blocks))

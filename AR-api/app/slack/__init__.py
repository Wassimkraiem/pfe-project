"""Slack notification module."""

from app.slack.services import send_webhook_message

__all__ = ["send_webhook_message"]

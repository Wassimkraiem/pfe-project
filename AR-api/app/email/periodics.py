"""Celery periodic tasks."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.core.config import settings
from app.email.services import (
    send_account_setup_reminder_email,
    send_pre_payment_reminder_email,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    name="email.periodics.send_pre_payment_reminder_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_pre_payment_reminder_email_task() -> None:
    """Periodic task that sends pre-payment reminder email."""
    asyncio.run(send_pre_payment_reminder_email())


@celery_app.task(
    name="email.periodics.send_account_setup_reminder_email",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def send_account_setup_reminder_email_task() -> None:
    """Periodic task that sends account setup reminder email."""
    asyncio.run(send_account_setup_reminder_email())


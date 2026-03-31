"""Celery application configuration."""

import asyncio
import logging

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "authentic_rights",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.email.tasks",
        "app.email.periodics",
        "app.onboarding_session.periodics",
        "app.canto.tasks",
        "app.slack.tasks",
        "app.payment.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Broker connection settings to prevent webhook timeouts
    broker_connection_timeout=10.0,  # 10 second connection timeout
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=3,
    # Redis-specific socket timeouts (fallback if URL doesn't specify)
    broker_transport_options={
        "socket_timeout": 10.0,
        "socket_connect_timeout": 5.0,
    },
)


@worker_process_init.connect
def _dispose_async_engine_on_worker_init(**kwargs: object) -> None:
    """Dispose async DB engine so workers create fresh connections in their event loop."""
    try:
        from app.db.database import async_engine

        asyncio.run(async_engine.dispose())
    except Exception as e:
        logger.warning("Could not dispose async engine on worker init: %s", e)


celery_app.conf.beat_schedule = {
    "send-pre-payment-reminder-email": {
        "task": "email.periodics.send_pre_payment_reminder_email",
        "schedule": 86400,
    },
    "send-account-setup-reminder-email": {
        "task": "email.periodics.send_account_setup_reminder_email",
        "schedule": 86400,  
    },
    "clean-up-stale-onboarding-sessions": {
        "task": "onboarding_session.periodics.clean_up_stale_onboarding_sessions",
        "schedule": 86400,
    },
}

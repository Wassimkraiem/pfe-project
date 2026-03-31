"""Celery tasks for Canto user provisioning and group access control."""

import logging

from app.celery_app import celery_app
from app.canto_sdk import BASIC_PLAN_GROUP, CantoUsers
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    name="canto.create_basic_user",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def create_basic_canto_user_task(
    user_email: str,
    first_name: str,
    last_name: str,
) -> bool | None:
    """Queue task to create a basic-plan Canto user.

    Only executes in prod environment when Canto is enabled.
    """
    if not settings.canto_enabled:
        logger.info(
            "Canto disabled (ENV=%s); skipping user creation for %s",
            settings.ENV,
            user_email,
        )
        return None

    try:
        CantoUsers().create_new_user_basic_plan(
            user_email=user_email,
            first_name=first_name,
            last_name=last_name,
        )
        logger.info("Created Canto basic-plan user: %s", user_email)
        return True
    except Exception:
        logger.exception("Failed to create Canto user for %s", user_email)
        raise


@celery_app.task(
    name="canto.remove_user_from_basic_group",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def remove_user_from_basic_group_task(user_email: str) -> bool | None:
    """Queue task to remove a user from Canto basic-plan group."""
    if not settings.canto_enabled:
        logger.info(
            "Canto disabled (ENV=%s); skipping group removal for %s",
            settings.ENV,
            user_email,
        )
        return None

    try:
        CantoUsers().remove_user_from_group(BASIC_PLAN_GROUP, user_email)
        logger.info("Removed Canto basic-plan group access: %s", user_email)
        return True
    except Exception:
        logger.exception("Failed to remove Canto basic-plan group access for %s", user_email)
        raise


@celery_app.task(
    name="canto.add_user_to_basic_group",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def add_user_to_basic_group_task(user_email: str) -> bool | None:
    """Queue task to add a user to Canto basic-plan group."""
    if not settings.canto_enabled:
        logger.info(
            "Canto disabled (ENV=%s); skipping group add for %s",
            settings.ENV,
            user_email,
        )
        return None

    try:
        CantoUsers().add_user_to_group(BASIC_PLAN_GROUP, user_email)
        logger.info("Added Canto basic-plan group access: %s", user_email)
        return True
    except Exception:
        logger.exception("Failed to add Canto basic-plan group access for %s", user_email)
        raise

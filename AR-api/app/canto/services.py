import asyncio
import logging

from app.canto.exceptions import CantoGroupRemovalFailed
from app.canto_sdk import BASIC_PLAN_GROUP, CantoUsers
from app.core.config import settings

logger = logging.getLogger(__name__)


class CantoService:
    def __init__(self) -> None:
        pass

    async def remove_user_from_basic_group(
        self,
        *,
        user_email: str,
    ) -> dict[str, object]:
        normalized_email = user_email.strip().lower()

        if not settings.canto_enabled:
            return {
                "mode": "direct",
                "email": normalized_email,
                "canto_enabled": settings.canto_enabled,
                "removed": False,
                "message": "Canto is disabled for this environment",
            }

        try:
            await asyncio.to_thread(
                CantoUsers().remove_user_from_group,
                BASIC_PLAN_GROUP,
                normalized_email,
            )
        except Exception as exc:
            logger.exception(
                "Manual Canto removal failed: email=%s group_id=%s",
                normalized_email,
                BASIC_PLAN_GROUP,
            )
            raise CantoGroupRemovalFailed(details=str(exc)) from exc

        logger.info(
            "Manual Canto removal succeeded: email=%s group_id=%s",
            normalized_email,
            BASIC_PLAN_GROUP,
        )
        return {
            "mode": "direct",
            "email": normalized_email,
            "group_id": BASIC_PLAN_GROUP,
            "canto_enabled": settings.canto_enabled,
            "removed": True,
        }

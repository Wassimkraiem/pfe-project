import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.core.config import settings
from app.onboarding_session.services import OnboardingSessionService

logger = logging.getLogger(__name__)


@celery_app.task(
    name="onboarding_session.periodics.clean_up_stale_onboarding_sessions",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 5},
)
def clean_up_stale_onboarding_sessions_task() -> None:
    """Periodic task that cleans up onboarding sessions stuck in PAGES step for over a week."""

    async def _run() -> None:
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
        )
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        try:
            async with session_factory() as db:
                try:
                    service = OnboardingSessionService(db=db)
                    await service.clean_up_stale_onboarding_sessions()
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise
        finally:
            await engine.dispose()

    asyncio.run(_run())
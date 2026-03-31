import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)

async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a transactional database session.

    The session automatically commits on successful request completion
    and rolls back on any unhandled exception.

    Usage:
        @router.post("/items")
        async def create_item(db: AsyncSession = Depends(get_db)):
            # All operations here are in a single transaction
            db.add(item)
            # Commit happens automatically after the endpoint returns
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def transaction_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for explicit transaction control.

    Use this for background tasks, CLI scripts, or when you need
    explicit transaction boundaries outside of FastAPI request scope.

    Usage:
        async with transaction_context() as session:
            session.add(item)
            # Commit happens at end of context
            # Rollback happens on exception
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "Base",
    "async_engine",
    "AsyncSessionLocal",
    "get_db",
    "transaction_context",
]


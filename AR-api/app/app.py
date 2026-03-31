import asyncio
import concurrent.futures
import logging
import os
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from http import HTTPStatus
from pathlib import Path

from app.auth.router import router as auth_router
from app.canto.router import router as canto_router
from app.channel.router import router as channel_router
from app.conversation.router import router as conversation_router
from app.core.config import settings
from app.db.database import async_engine
from app.exceptionhandler import setup_exception_handlers
from app.onboarding_session.router import router as onboarding_router
from app.payment.router import router as payment_router
from app.payment.webhook_router import router as webhook_router
from app.playlist.router import router as playlist_router
from app.user.router import router as user_router
from app.video_submission.router import router as video_submission_router
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from starlette.responses import Response
from sqlalchemy import text
#prod
if settings.sentry_enabled:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        send_default_pii=True,
        environment=settings.ENV,
    )

app = FastAPI(title=settings.PROJECT_NAME)
logger = logging.getLogger(__name__)

# CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_exception_handlers(app)
# Register webhook router FIRST to ensure it's matched before other routes
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(canto_router)
app.include_router(onboarding_router)
app.include_router(channel_router)
app.include_router(conversation_router)
app.include_router(playlist_router)
app.include_router(video_submission_router)
app.include_router(payment_router)


def _get_alembic_config() -> Config:
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    return Config(str(alembic_ini))


def _log_startup_step(
    *,
    step: str,
    status: str,
    duration_ms: int | None = None,
    timeout_seconds: float | None = None,
    optional: bool = False,
    details: str | None = None,
) -> None:
    logger.info(
        (
            "startup step=%s status=%s duration_ms=%s timeout_seconds=%s "
            "optional=%s details=%s"
        ),
        step,
        status,
        duration_ms,
        timeout_seconds,
        optional,
        details,
    )


async def _run_startup_step(
    *,
    step: str,
    action: Callable[[], Awaitable[None]],
    timeout_seconds: float | None,
    optional: bool = False,
) -> None:
    _log_startup_step(
        step=step,
        status="start",
        timeout_seconds=timeout_seconds,
        optional=optional,
    )
    started = time.perf_counter()
    try:
        if timeout_seconds is None:
            await action()
        else:
            await asyncio.wait_for(action(), timeout=timeout_seconds)
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _log_startup_step(
            step=step,
            status="failed",
            duration_ms=duration_ms,
            timeout_seconds=timeout_seconds,
            optional=optional,
        )
        logger.exception("Startup step failed: %s", step)
        if not optional:
            raise
    else:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _log_startup_step(
            step=step,
            status="end",
            duration_ms=duration_ms,
            timeout_seconds=timeout_seconds,
            optional=optional,
        )


async def _startup_load_settings() -> None:
    _ = settings.PROJECT_NAME
    _ = settings.DATABASE_URL
    _ = settings.CELERY_BROKER_URL


async def _startup_secrets_config_fetch() -> None:
    pass


async def _startup_db_ping() -> None:
    async with async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def _startup_redis_ping() -> None:
    broker_url = settings.CELERY_BROKER_URL.strip()
    if not broker_url.lower().startswith(("redis://", "rediss://")):
        _log_startup_step(
            step="redis_connect_ping",
            status="skipped",
            details=f"Unsupported broker URL scheme: {broker_url}",
            optional=True,
        )
        return
    try:
        import redis.asyncio as redis
    except ImportError:
        _log_startup_step(
            step="redis_connect_ping",
            status="skipped",
            details="redis package is not installed.",
            optional=True,
        )
        return
    redis_client = redis.from_url(
        broker_url,
        socket_connect_timeout=settings.STARTUP_STEP_TIMEOUT_SECONDS,
        socket_timeout=settings.STARTUP_STEP_TIMEOUT_SECONDS,
    )
    try:
        await redis_client.ping()
    finally:
        with suppress(Exception):
            await redis_client.aclose()


async def _startup_external_checks() -> None:
    if not settings.STARTUP_ENABLE_EXTERNAL_CHECKS:
        _log_startup_step(
            step="external_http_checks",
            status="skipped",
            details="External checks are disabled by STARTUP_ENABLE_EXTERNAL_CHECKS.",
            optional=True,
        )
        return
    check_urls = [settings.CLERK_JWKS_URL]
    async with httpx.AsyncClient(
        timeout=settings.STARTUP_EXTERNAL_CHECK_TIMEOUT_SECONDS
    ) as client:
        for url in check_urls:
            if not url:
                continue
            response = await client.get(url)
            logger.info(
                "startup step=%s url=%s status_code=%s",
                "external_http_checks",
                url,
                response.status_code,
            )


async def _startup_dynamodb_ping() -> None:
    if not settings.STARTUP_ENABLE_DDB_CHECK:
        _log_startup_step(
            step="dynamodb_connect_check",
            status="skipped",
            details="DynamoDB check is disabled by STARTUP_ENABLE_DDB_CHECK.",
            optional=True,
        )
        return

    table_name = settings.DDB_TABLE_NAME.strip()
    if not table_name:
        _log_startup_step(
            step="dynamodb_connect_check",
            status="skipped",
            details="DDB_TABLE_NAME is empty.",
            optional=True,
        )
        return

    region_name = (
        settings.DDB_REGION.strip()
        or os.getenv("AWS_REGION", "").strip()
        or os.getenv("AWS_DEFAULT_REGION", "").strip()
    )
    if not region_name:
        _log_startup_step(
            step="dynamodb_connect_check",
            status="skipped",
            details="No region configured. Set DDB_REGION or AWS_REGION.",
            optional=True,
        )
        return

    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except ImportError:
        _log_startup_step(
            step="dynamodb_connect_check",
            status="skipped",
            details="boto3 is not installed.",
            optional=True,
        )
        return

    endpoint_url = settings.DDB_ENDPOINT_URL.strip() or None

    def _ping_table() -> str:
        client = boto3.client(
            "dynamodb",
            region_name=region_name,
            endpoint_url=endpoint_url,
            config=BotoConfig(
                connect_timeout=settings.STARTUP_DDB_CHECK_TIMEOUT_SECONDS,
                read_timeout=settings.STARTUP_DDB_CHECK_TIMEOUT_SECONDS,
                retries={"max_attempts": 1},
            ),
        )
        response = client.describe_table(TableName=table_name)
        return response["Table"]["TableStatus"]

    table_status = await asyncio.to_thread(_ping_table)
    logger.info(
        "startup step=%s table_name=%s region=%s endpoint_url=%s table_status=%s",
        "dynamodb_connect_check",
        table_name,
        region_name,
        endpoint_url,
        table_status,
    )


@app.on_event("startup")
async def startup() -> None:
    loop = asyncio.get_event_loop()
    loop.set_default_executor(
        concurrent.futures.ThreadPoolExecutor(
            max_workers=settings.ASYNCIO_THREAD_POOL_SIZE,
            thread_name_prefix="asyncio_worker",
        )
    )
    logger.info(
        "startup thread_pool max_workers=%s", settings.ASYNCIO_THREAD_POOL_SIZE
    )
    logger.info("startup status=start")
    startup_started = time.perf_counter()
    try:
        await _run_startup_step(
            step="load_settings_env",
            action=_startup_load_settings,
            timeout_seconds=None,
        )
        await _run_startup_step(
            step="secrets_config_fetch",
            action=_startup_secrets_config_fetch,
            timeout_seconds=None,
        )
        await _run_startup_step(
            step="db_connect_ping",
            action=_startup_db_ping,
            timeout_seconds=settings.STARTUP_STEP_TIMEOUT_SECONDS,
        )
        await _run_startup_step(
            step="redis_connect_ping",
            action=_startup_redis_ping,
            timeout_seconds=settings.STARTUP_STEP_TIMEOUT_SECONDS,
            optional=True,
        )
        await _run_startup_step(
            step="external_http_checks",
            action=_startup_external_checks,
            timeout_seconds=settings.STARTUP_STEP_TIMEOUT_SECONDS,
            optional=True,
        )
        await _run_startup_step(
            step="dynamodb_connect_check",
            action=_startup_dynamodb_ping,
            timeout_seconds=settings.STARTUP_DDB_CHECK_TIMEOUT_SECONDS,
            optional=True,
        )

    except Exception:
        total_duration_ms = int((time.perf_counter() - startup_started) * 1000)
        logger.exception("startup status=failed duration_ms=%s", total_duration_ms)
        raise
    total_duration_ms = int((time.perf_counter() - startup_started) * 1000)
    logger.info("startup status=end duration_ms=%s", total_duration_ms)


@app.get("/health")
async def health() -> dict[str, str | int]:
    return {"status": "ok", "version": 3}


@app.get("/health/env")
def health_env() -> dict[str, str | bool]:
    """Debug endpoint to verify environment configuration."""
    return {
        "env": settings.ENV,
        "is_local": settings.is_local,
        "is_staging": settings.is_staging,
        "is_prod": settings.is_prod,
        "canto_enabled": settings.canto_enabled,
        "sentry_enabled": settings.sentry_enabled,
    }


@app.get("/db")
async def health_db() -> JSONResponse:
    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_cfg)
    expected_heads = set(script.get_heads())

    db_ok = False
    current_heads: set[str] = set()
    async with async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        db_ok = True

        def _get_current_heads(sync_conn):
            context = MigrationContext.configure(sync_conn)
            return context.get_current_heads()

        current_heads = set(await conn.run_sync(_get_current_heads))

    migrations_ok = current_heads == expected_heads
    status_code = HTTPStatus.OK if db_ok and migrations_ok else HTTPStatus.SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if status_code == HTTPStatus.OK else "degraded",
            "db": db_ok,
            "migrations_ok": migrations_ok,
            "current_heads": sorted(current_heads),
            "expected_heads": sorted(expected_heads),
        },
    )

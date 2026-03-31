import asyncio
from logging.config import fileConfig

from alembic import context  # type: ignore[attr-defined]
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.db.base import Base

# Ensure models are imported so Alembic can see them in metadata (side effects)
import app.user  # noqa: F401
import app.onboarding_session  # noqa: F401
import app.channel  # noqa: F401
import app.email  # noqa: F401
import app.payment  # noqa: F401
import app.conversation  # noqa: F401
import app.playlist  # noqa: F401
import app.video_submission  # noqa: F401


config = context.config  # type: ignore[attr-defined]

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def get_url() -> str:
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(  # type: ignore[attr-defined]
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():  # type: ignore[attr-defined]
        context.run_migrations()  # type: ignore[attr-defined]


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    def do_run_migrations(connection) -> None:
        context.configure(  # type: ignore[attr-defined]
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():  # type: ignore[attr-defined]
            context.run_migrations()  # type: ignore[attr-defined]

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():  # type: ignore[attr-defined]
    run_migrations_offline()
else:
    run_migrations_online()

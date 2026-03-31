from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.chat import router as chat_router
from app.api.rag import router as rag_router
from app.core.chatbot_init import init_chatbot
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import chat, knowledge  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_chatbot(app)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE IF EXISTS chat_sessions ADD COLUMN IF NOT EXISTS user_id VARCHAR(255)"))
        await conn.execute(
            text(
                "UPDATE chat_sessions SET user_id = CONCAT('legacy-user-', id) "
                "WHERE user_id IS NULL OR user_id = ''"
            )
        )
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(chat_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

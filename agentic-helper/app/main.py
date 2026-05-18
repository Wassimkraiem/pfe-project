from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.rag import router as rag_router
from app.api.transcribe import router as transcribe_router
from app.core.chatbot_init import init_chatbot
from app.core.config import settings
from app.services.chat_history import build_chat_history_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_chatbot(app)
    app.state.chat_history_store = await build_chat_history_store(
        max_messages=settings.chat_memory_messages,
        redis_url=settings.chat_history_redis_url,
        ttl_seconds=settings.chat_history_ttl_seconds,
    )
    yield

    video_search_client = getattr(app.state, "video_search_client", None)
    close = getattr(video_search_client, "close", None)
    if close is not None:
        result = close()
        if hasattr(result, "__await__"):
            await result

    history_store = getattr(app.state, "chat_history_store", None)
    close = getattr(history_store, "close", None)
    if close is not None:
        result = close()
        if hasattr(result, "__await__"):
            await result

    qdrant_client = getattr(app.state, "qdrant_client", None)
    close = getattr(qdrant_client, "close", None)
    if close is not None:
        result = close()
        if hasattr(result, "__await__"):
            await result


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(chat_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(transcribe_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

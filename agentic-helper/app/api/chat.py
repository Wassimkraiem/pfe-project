from urllib.parse import urlencode

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_chat_service, get_db, get_user_id
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, SourceItem
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def _build_frontend_search_url(search_filters: dict) -> str:
    if not search_filters:
        return settings.frontend_search_url

    params: list[tuple[str, str]] = []

    query = search_filters.get("query")
    if isinstance(query, str) and query.strip():
        params.append(("q", query.strip()))

    list_keys = ("categories", "tags", "locations", "resolutions", "orientation")
    for key in list_keys:
        values = search_filters.get(key)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str) and value.strip():
                    params.append((key, value.strip()))

    scalar_keys = ("duration_min", "duration_max", "video_id")
    for key in scalar_keys:
        value = search_filters.get(key)
        if value is None:
            continue
        params.append((key, str(value)))

    if not params:
        return settings.frontend_search_url

    return f"{settings.frontend_search_url}?{urlencode(params, doseq=True)}"


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    if payload.mode == "video_search":
        _, videos, search_filters = await chat_service.ask_video_search(
            db, user_id=user_id, question=payload.input_message
        )
        search_url = _build_frontend_search_url(search_filters)
        search_action = {
            "type": "apply_video_search",
            "auto_apply": True,
            "filters": search_filters,
            "url": search_url,
        }
        return ChatResponse(
            answer="",
            videos=videos if videos else None,
            search_filters=search_filters if search_filters else None,
            search_action=search_action,
            search_url=search_url,
        )

    answer, chunks, interest_label = await chat_service.ask(db, user_id=user_id, question=payload.input_message)
    sources = [SourceItem(chunk_id=chunk.id, source=chunk.source) for chunk in chunks]
    return ChatResponse(answer=answer, interest_label=interest_label, sources=sources)

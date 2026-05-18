from urllib.parse import urlencode

from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service, get_user_id
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, CitationItem, SourceItem
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

    scalar_keys = (
        "duration_min",
        "duration_max",
        "video_id",
        "k",
        "offset",
        "limit",
        "sort_by",
        "sort_order",
    )
    for key in scalar_keys:
        value = search_filters.get(key)
        if value is None:
            continue
        params.append((key, str(value)))

    if not params:
        return settings.frontend_search_url

    return f"{settings.frontend_search_url}?{urlencode(params, doseq=True)}"


def _sources_and_citations(chunks) -> tuple[list[SourceItem], list[CitationItem]]:
    sources = [SourceItem(chunk_id=chunk.id, source=chunk.source) for chunk in chunks]
    citations = [
        CitationItem(
            chunk_id=chunk.id,
            source=chunk.source,
            score=getattr(chunk, "score", None),
            excerpt=str(getattr(chunk, "content", ""))[:240],
        )
        for chunk in chunks
    ]
    return sources, citations


def _video_search_response(
    *,
    answer: str,
    videos: list[dict] | None,
    search_filters: dict,
    route: str = "VIDEO_SEARCH",
    confidence: float | None = None,
    total: int | None = None,
    next_offset: int | None = None,
    execution: dict | None = None,
    fallbacks_used: list[str] | None = None,
) -> ChatResponse:
    search_url = _build_frontend_search_url(search_filters)
    search_action = {
        "type": "apply_video_search",
        "auto_apply": True,
        "filters": search_filters,
        "url": search_url,
    }
    return ChatResponse(
        answer=answer,
        route=route,
        confidence=confidence,
        videos=videos if videos else None,
        search_filters=search_filters if search_filters else None,
        search_action=search_action,
        search_url=search_url,
        total=total,
        next_offset=next_offset,
        execution=execution,
        fallbacks_used=fallbacks_used,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user_id: str = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    if payload.mode == "video_search":
        if hasattr(chat_service, "ask_video_search_detailed"):
            result = await chat_service.ask_video_search_detailed(
                user_id=user_id,
                question=payload.input_message,
                debug=payload.debug,
            )
            return _video_search_response(
                answer=result.answer if payload.include_answer else "",
                videos=result.videos,
                search_filters=result.filters,
                total=result.total,
                next_offset=result.next_offset,
                execution=result.execution,
                fallbacks_used=result.fallbacks_used,
            )

        _, videos, search_filters = await chat_service.ask_video_search(
            user_id=user_id,
            question=payload.input_message,
        )
        return _video_search_response(answer="", videos=videos, search_filters=search_filters)

    if payload.mode == "auto":
        result = await chat_service.ask_auto(
            user_id=user_id,
            question=payload.input_message,
            include_answer=payload.include_answer,
            debug=payload.debug,
        )
        if result.video_result is not None:
            return _video_search_response(
                answer=result.answer,
                videos=result.video_result.videos,
                search_filters=result.video_result.filters,
                route=result.route,
                confidence=result.confidence,
                total=result.video_result.total,
                next_offset=result.video_result.next_offset,
                execution=result.video_result.execution,
                fallbacks_used=result.video_result.fallbacks_used,
            )

        chunks = result.chunks or []
        sources, citations = _sources_and_citations(chunks)
        return ChatResponse(
            answer=result.answer,
            route=result.route,
            confidence=result.confidence,
            interest_label=result.interest_label,
            sources=sources,
            citations=citations,
        )

    answer, chunks, interest_label = await chat_service.ask(user_id=user_id, question=payload.input_message)
    sources, citations = _sources_and_citations(chunks)
    return ChatResponse(
        answer=answer,
        interest_label=interest_label,
        route="CHAT_RAG",
        sources=sources,
        citations=citations,
    )

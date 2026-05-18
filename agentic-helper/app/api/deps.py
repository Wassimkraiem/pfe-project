from fastapi import Depends, Header, HTTPException, Request, status

from app.core.chatbot_init import get_chatbot_runtime
from app.core.config import settings
from app.core.qdrant import build_qdrant_client, ensure_qdrant_collection
from app.services.chat import ChatService
from app.services.chat_history import ChatHistoryStore, InMemoryChatHistoryStore
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.services.rag import RagService
from app.services.video_search import VideoSearchService


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != settings.app_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")


def get_user_id(
    _: None = Depends(require_api_key),
    x_user_id: str = Header(default="default-user"),
) -> str:
    user_id = x_user_id.strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="x-user-id cannot be empty")
    return user_id


async def get_rag_service(request: Request) -> RagService:
    embeddings = EmbeddingService()
    qdrant_client = getattr(request.app.state, "qdrant_client", None)
    if qdrant_client is None:
        qdrant_client = build_qdrant_client()
        await ensure_qdrant_collection(qdrant_client)
        request.app.state.qdrant_client = qdrant_client
    return RagService(embeddings=embeddings, qdrant_client=qdrant_client)


async def get_chat_history_store(request: Request) -> ChatHistoryStore:
    history_store = getattr(request.app.state, "chat_history_store", None)
    if history_store is None:
        history_store = InMemoryChatHistoryStore(max_messages=settings.chat_memory_messages)
        request.app.state.chat_history_store = history_store
    return history_store


async def get_chat_service(
    request: Request,
    rag: RagService = Depends(get_rag_service),
    history_store: ChatHistoryStore = Depends(get_chat_history_store),
) -> ChatService:
    runtime = get_chatbot_runtime(request.app)
    llm = LLMService(model=runtime.llm, classifier_model=runtime.classifier_llm)
    video_search_service = None
    if settings.video_search_advanced_enabled and runtime.video_search_client is not None:
        video_search_service = VideoSearchService(
            client=runtime.video_search_client,
            filter_llm=runtime.video_filter_llm,
            filter_prompt=runtime.video_filter_extractor_prompt,
            llm_service=llm,
            query_rewrite_prompt=runtime.video_search_query_rewrite_prompt,
        )
    return ChatService(
        rag_service=rag,
        history_store=history_store,
        llm_service=llm,
        system_prompt=runtime.system_prompt,
        rag_classifier_prompt=runtime.rag_classifier_prompt,
        router_prompt=runtime.router_prompt,
        interest_classifier_prompt=runtime.interest_classifier_prompt,
        interested_response_prompt=runtime.interested_response_prompt,
        not_interested_response_prompt=runtime.not_interested_response_prompt,
        video_filter_extractor_prompt=runtime.video_filter_extractor_prompt,
        video_search_agent=runtime.video_search_agent,
        video_filter_llm=runtime.video_filter_llm,
        video_search_service=video_search_service,
        rag_query_rewrite_prompt=runtime.rag_query_rewrite_prompt,
        rag_chunk_grading_prompt=runtime.rag_chunk_grading_prompt,
    )


__all__ = ["require_api_key", "get_user_id", "get_chat_service", "get_rag_service", "get_chat_history_store"]

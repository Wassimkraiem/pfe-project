import logging

from fastapi import FastAPI
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.langsmith import configure_langsmith, resolve_prompt_text
from app.services.agent import build_agent_llm, build_video_search_agent
from app.services.chatbot_runtime import ChatbotRuntime
from app.services.video_search import AdvancedVideoSearchClient


logger = logging.getLogger(__name__)


async def init_chatbot(app: FastAPI) -> None:
    logger.info("Initializing chatbot runtime")
    configure_langsmith()

    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        temperature=settings.openai_chat_temperature,
    )
    classifier_llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_classifier_model,
        temperature=settings.openai_classifier_temperature,
    )
    video_filter_llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_agent_model,
        temperature=0.0,
    )

    video_search_system_prompt = resolve_prompt_text(
        prompt_name="video_search_system_prompt",
        langsmith_prompt=settings.video_search_system_prompt_langsmith,
        prompt_file_path=settings.video_search_system_prompt_file,
        fallback_prompt=settings.video_search_system_prompt,
    )
    agent_llm = build_agent_llm()
    video_search_agent = build_video_search_agent(agent_llm, system_prompt=video_search_system_prompt)
    video_search_client = AdvancedVideoSearchClient.from_settings()
    app.state.video_search_client = video_search_client
    logger.info("Video search agent initialized with model=%s", settings.openai_agent_model)

    app.state.chatbot_runtime = ChatbotRuntime(
        llm=llm,
        classifier_llm=classifier_llm,
        video_filter_llm=video_filter_llm,
        system_prompt=resolve_prompt_text(
            prompt_name="chatbot_system_prompt",
            langsmith_prompt=settings.chatbot_system_prompt_langsmith,
            prompt_file_path=settings.chatbot_system_prompt_file,
            fallback_prompt=settings.chatbot_system_prompt,
        ),
        rag_classifier_prompt=resolve_prompt_text(
            prompt_name="chatbot_rag_classifier_prompt",
            langsmith_prompt=settings.chatbot_rag_classifier_prompt_langsmith,
            prompt_file_path=settings.chatbot_rag_classifier_prompt_file,
            fallback_prompt=settings.chatbot_rag_classifier_prompt,
        ),
        router_prompt=resolve_prompt_text(
            prompt_name="chatbot_router_prompt",
            langsmith_prompt=settings.chatbot_router_prompt_langsmith,
            prompt_file_path=settings.chatbot_router_prompt_file,
            fallback_prompt=settings.chatbot_router_prompt,
        ),
        interest_classifier_prompt=resolve_prompt_text(
            prompt_name="chatbot_interest_classifier_prompt",
            langsmith_prompt=settings.chatbot_interest_classifier_prompt_langsmith,
            prompt_file_path=settings.chatbot_interest_classifier_prompt_file,
            fallback_prompt=settings.chatbot_interest_classifier_prompt,
        ),
        interested_response_prompt=resolve_prompt_text(
            prompt_name="chatbot_interested_response_prompt",
            langsmith_prompt=settings.chatbot_interested_response_prompt_langsmith,
            prompt_file_path=settings.chatbot_interested_response_prompt_file,
            fallback_prompt=settings.chatbot_interested_response_prompt,
        ),
        not_interested_response_prompt=resolve_prompt_text(
            prompt_name="chatbot_not_interested_response_prompt",
            langsmith_prompt=settings.chatbot_not_interested_response_prompt_langsmith,
            prompt_file_path=settings.chatbot_not_interested_response_prompt_file,
            fallback_prompt=settings.chatbot_not_interested_response_prompt,
        ),
        video_filter_extractor_prompt=resolve_prompt_text(
            prompt_name="chatbot_video_filter_extractor_prompt",
            langsmith_prompt=settings.chatbot_video_filter_extractor_prompt_langsmith,
            prompt_file_path=settings.chatbot_video_filter_extractor_prompt_file,
            fallback_prompt=settings.chatbot_video_filter_extractor_prompt,
        ),
        rag_query_rewrite_prompt=resolve_prompt_text(
            prompt_name="rag_query_rewrite_prompt",
            langsmith_prompt="",
            prompt_file_path=settings.rag_query_rewrite_prompt_file,
            fallback_prompt=settings.rag_query_rewrite_prompt,
        ),
        rag_chunk_grading_prompt=resolve_prompt_text(
            prompt_name="rag_chunk_grading_prompt",
            langsmith_prompt="",
            prompt_file_path=settings.rag_chunk_grading_prompt_file,
            fallback_prompt=settings.rag_chunk_grading_prompt,
        ),
        video_search_query_rewrite_prompt=resolve_prompt_text(
            prompt_name="video_search_query_rewrite_prompt",
            langsmith_prompt="",
            prompt_file_path=settings.video_search_query_rewrite_prompt_file,
            fallback_prompt=settings.video_search_query_rewrite_prompt,
        ),
        video_search_agent=video_search_agent,
        video_search_client=video_search_client,
    )
    logger.info(
        "Chatbot runtime initialized with chat_model=%s classifier_model=%s",
        settings.openai_chat_model,
        settings.openai_classifier_model,
    )


def get_chatbot_runtime(app: FastAPI) -> ChatbotRuntime:
    runtime = getattr(app.state, "chatbot_runtime", None)
    if runtime is None:
        raise RuntimeError("chatbot runtime not initialized")
    return runtime

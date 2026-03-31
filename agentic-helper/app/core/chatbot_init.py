import logging
from pathlib import Path

from fastapi import FastAPI
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.agent import build_agent_llm, build_video_search_agent
from app.services.chatbot_runtime import ChatbotRuntime


logger = logging.getLogger(__name__)


def _resolve_prompt(prompt_file_path: str, fallback_prompt: str) -> str:
    prompt_file = Path(prompt_file_path)
    if prompt_file.exists():
        content = prompt_file.read_text(encoding="utf-8").strip()
        if content:
            return content
    return fallback_prompt


async def init_chatbot(app: FastAPI) -> None:
    logger.info("Initializing chatbot runtime")

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

    agent_llm = build_agent_llm()
    video_search_agent = build_video_search_agent(agent_llm)
    logger.info("Video search agent initialized with model=%s", settings.openai_agent_model)

    app.state.chatbot_runtime = ChatbotRuntime(
        llm=llm,
        classifier_llm=classifier_llm,
        video_filter_llm=video_filter_llm,
        system_prompt=_resolve_prompt(
            settings.chatbot_system_prompt_file,
            settings.chatbot_system_prompt,
        ),
        rag_classifier_prompt=settings.chatbot_rag_classifier_prompt,
        interest_classifier_prompt=settings.chatbot_interest_classifier_prompt,
        interested_response_prompt=settings.chatbot_interested_response_prompt,
        not_interested_response_prompt=settings.chatbot_not_interested_response_prompt,
        video_filter_extractor_prompt=_resolve_prompt(
            settings.chatbot_video_filter_extractor_prompt_file,
            settings.chatbot_video_filter_extractor_prompt,
        ),
        video_search_agent=video_search_agent,
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

from __future__ import annotations

import os
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langsmith import Client

from app.core.config import settings


def _read_prompt(path_str: str, fallback: str) -> str:
    path = Path(path_str)
    if path.exists():
        content = path.read_text(encoding="utf-8").strip()
        if content:
            return content
    return fallback


def main() -> None:
    os.environ.setdefault("LANGSMITH_TRACING", "false")

    client = Client(
        api_key=settings.langsmith_api_key,
        api_url=settings.langsmith_endpoint,
    )

    prompt_map = {
        "CHATBOT_SYSTEM_PROMPT_LANGSMITH": {
            "name": "agentic-helper-chatbot-system",
            "text": _read_prompt(settings.chatbot_system_prompt_file, settings.chatbot_system_prompt),
            "description": "Primary BVIRAL chatbot system prompt.",
        },
        "CHATBOT_INTEREST_CLASSIFIER_PROMPT_LANGSMITH": {
            "name": "agentic-helper-chatbot-interest-classifier",
            "text": settings.chatbot_interest_classifier_prompt,
            "description": "Classifier for interested vs not interested vs unclear user intent.",
        },
        "CHATBOT_INTERESTED_RESPONSE_PROMPT_LANGSMITH": {
            "name": "agentic-helper-chatbot-interested-response",
            "text": settings.chatbot_interested_response_prompt,
            "description": "Response-mode prompt for interested users.",
        },
        "CHATBOT_NOT_INTERESTED_RESPONSE_PROMPT_LANGSMITH": {
            "name": "agentic-helper-chatbot-not-interested-response",
            "text": settings.chatbot_not_interested_response_prompt,
            "description": "Response-mode prompt for not interested users.",
        },
        "CHATBOT_VIDEO_FILTER_EXTRACTOR_PROMPT_LANGSMITH": {
            "name": "agentic-helper-chatbot-video-filter-extractor",
            "text": _read_prompt(
                settings.chatbot_video_filter_extractor_prompt_file,
                settings.chatbot_video_filter_extractor_prompt,
            ),
            "description": "Structured filter extractor for BVIRAL video search.",
        },
        "VIDEO_SEARCH_SYSTEM_PROMPT_LANGSMITH": {
            "name": "agentic-helper-video-search-system",
            "text": _read_prompt(
                settings.video_search_system_prompt_file,
                settings.video_search_system_prompt,
            ),
            "description": "System prompt for the BVIRAL video search agent.",
        },
    }

    for env_var, item in prompt_map.items():
        prompt = PromptTemplate.from_template(item["text"])
        prompt_identifier = item["name"]
        client.push_prompt(
            prompt_identifier,
            object=prompt,
            description=item["description"],
            tags=["agentic-helper", "bviral"],
            commit_tags=["latest"],
        )
        print(f"{env_var}={prompt_identifier}")


if __name__ == "__main__":
    main()

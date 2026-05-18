from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from langsmith import Client
except ImportError:  # pragma: no cover - optional until dependencies are installed
    Client = None  # type: ignore[assignment]


def configure_langsmith() -> None:
    if settings.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "true"
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    if settings.langsmith_project:
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_workspace_id:
        os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id


@lru_cache(maxsize=1)
def get_langsmith_client() -> Any | None:
    if Client is None:
        logger.warning("LangSmith SDK is not installed; LangSmith prompt loading is unavailable")
        return None
    if not settings.langsmith_api_key:
        return None
    return Client()


def _prompt_to_text(prompt: Any) -> str:
    template = getattr(prompt, "template", None)
    if isinstance(template, str) and template.strip():
        return template.strip()

    messages = getattr(prompt, "messages", None)
    if isinstance(messages, list):
        rendered: list[str] = []
        for message in messages:
            nested_prompt = getattr(message, "prompt", None)
            nested_template = getattr(nested_prompt, "template", None)
            if isinstance(nested_template, str) and nested_template.strip():
                rendered.append(nested_template.strip())
                continue

            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                rendered.append(content.strip())

        text = "\n\n".join(rendered).strip()
        if text:
            return text

    rendered = str(prompt).strip()
    if rendered:
        return rendered

    raise ValueError("Prompt content is empty")


@lru_cache(maxsize=32)
def pull_langsmith_prompt(identifier: str) -> str | None:
    prompt_id = identifier.strip()
    if not prompt_id:
        return None

    client = get_langsmith_client()
    if client is None:
        return None

    prompt = client.pull_prompt(prompt_id)
    return _prompt_to_text(prompt)


def resolve_prompt_text(
    *,
    prompt_name: str,
    langsmith_prompt: str = "",
    prompt_file_path: str | None = None,
    fallback_prompt: str,
) -> str:
    if langsmith_prompt.strip():
        try:
            resolved = pull_langsmith_prompt(langsmith_prompt)
            if resolved:
                logger.info("Loaded %s from LangSmith prompt %s", prompt_name, langsmith_prompt)
                return resolved
        except Exception:
            logger.exception("Failed to load %s from LangSmith prompt %s", prompt_name, langsmith_prompt)

    if prompt_file_path:
        prompt_file = Path(prompt_file_path)
        if prompt_file.exists():
            content = prompt_file.read_text(encoding="utf-8").strip()
            if content:
                logger.info("Loaded %s from file %s", prompt_name, prompt_file_path)
                return content

    logger.info("Loaded %s from fallback configuration", prompt_name)
    return fallback_prompt

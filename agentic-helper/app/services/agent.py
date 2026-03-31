"""LangChain tool-calling agent for video search."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from app.core.config import settings
from app.tools import ALL_VIDEO_TOOLS

logger = logging.getLogger(__name__)

_VIDEO_SEARCH_PROMPT_FILE = Path("data/prompts/video_search_system_prompt.txt")


class VideoSearchFilterPlan(BaseModel):
    method: Literal["auto", "semantic", "filters"] = "auto"
    query: str = ""
    k: int = Field(default=10, ge=1, le=50)
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    duration_min: float | None = None
    duration_max: float | None = None
    locations: list[str] = Field(default_factory=list)
    resolutions: list[str] = Field(default_factory=list)
    orientation: list[str] = Field(default_factory=list)
    video_id: str | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=50)


def _load_system_prompt() -> str:
    if _VIDEO_SEARCH_PROMPT_FILE.exists():
        content = _VIDEO_SEARCH_PROMPT_FILE.read_text(encoding="utf-8").strip()
        if content:
            return content
    return (
        "You are a video search assistant. Help users find videos using the available tools. "
        "Present results clearly with video titles, descriptions, and IDs."
    )


def build_agent_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_agent_model,
        temperature=settings.openai_agent_temperature,
    )


def build_video_search_agent(llm: ChatOpenAI):
    """Build a LangGraph ReAct agent with video search tools."""
    system_prompt = _load_system_prompt()
    return create_react_agent(
        model=llm,
        tools=ALL_VIDEO_TOOLS,
        prompt=system_prompt,
    )


def _compact_list(items: list[str]) -> list[str]:
    return [item.strip() for item in items if isinstance(item, str) and item.strip()]


def _normalize_filter_plan(plan: VideoSearchFilterPlan, question: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "method": plan.method,
        "query": plan.query.strip() or question,
        "k": plan.k,
        "offset": plan.offset,
        "limit": plan.limit,
    }
    for key in ("categories", "tags", "locations", "resolutions", "orientation"):
        values = _compact_list(getattr(plan, key))
        if values:
            normalized[key] = values
    if plan.duration_min is not None:
        normalized["duration_min"] = plan.duration_min
    if plan.duration_max is not None:
        normalized["duration_max"] = plan.duration_max
    if plan.video_id and plan.video_id.strip():
        normalized["video_id"] = plan.video_id.strip()
        if normalized["method"] == "auto":
            normalized["method"] = "filters"
    return normalized


async def extract_video_search_filters(
    llm: ChatOpenAI,
    question: str,
    filter_prompt: str,
    history_text: str = "",
) -> dict[str, Any]:
    """Extract structured video-search filters from user input."""
    prompt = ChatPromptTemplate.from_template(filter_prompt)
    structured_model = llm.with_structured_output(VideoSearchFilterPlan)
    chain = prompt | structured_model
    result = await chain.ainvoke(
        {
            "history_text": history_text or "No prior messages.",
            "question": question,
        }
    )
    return _normalize_filter_plan(result, question)


def _build_message_history(history_text: str) -> list:
    """Convert plain history text into LangChain message objects."""
    messages = []
    if not history_text or history_text == "No prior messages.":
        return messages
    for line in history_text.strip().split("\n"):
        if line.startswith("user: "):
            messages.append(HumanMessage(content=line[6:]))
        elif line.startswith("assistant: "):
            messages.append(AIMessage(content=line[11:]))
    return messages


def _extract_videos_from_messages(messages: list) -> list[dict]:
    """Scan agent output messages for JSON video arrays returned by tools."""
    videos: list[dict] = []
    seen_ids: set[str] = set()

    for msg in messages:
        if not hasattr(msg, "content"):
            continue
        content = msg.content if isinstance(msg.content, str) else ""
        if not content:
            continue
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue

        items = []
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict) and "videos" in parsed:
            items = parsed["videos"]

        for item in items:
            if isinstance(item, dict) and "video_id" in item:
                vid = item["video_id"]
                if vid not in seen_ids:
                    seen_ids.add(vid)
                    videos.append(item)

    return videos


async def run_video_search_agent(
    agent,
    filter_llm: ChatOpenAI,
    question: str,
    filter_prompt: str,
    history_text: str = "",
) -> tuple[str, list[dict], dict[str, Any]]:
    """Invoke the video search agent and return (answer_text, videos_list, applied_filters)."""
    try:
        filter_plan = await extract_video_search_filters(
            llm=filter_llm,
            question=question,
            filter_prompt=filter_prompt,
            history_text=history_text,
        )
    except Exception:
        logger.exception("Video filter extraction failed")
        filter_plan = {"method": "auto", "query": question, "k": 10, "offset": 0, "limit": 10}

    history_messages = _build_message_history(history_text)
    filter_context = json.dumps(filter_plan, ensure_ascii=False)
    enriched_question = (
        f"{question}\n\n"
        "Extracted filters from the user request. Apply these when calling tools:\n"
        f"{filter_context}"
    )
    input_messages = history_messages + [HumanMessage(content=enriched_question)]

    try:
        result = await agent.ainvoke({"messages": input_messages})
    except Exception:
        logger.exception("Video search agent invocation failed")
        return (
            "I couldn't reach the video search service right now. Please try again in a moment.",
            [],
            filter_plan,
        )

    all_messages = result.get("messages", [])

    answer = ""
    for msg in reversed(all_messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            answer = msg.content
            break

    if not answer:
        answer = "I searched for videos but couldn't formulate a response. Please try rephrasing your request."

    videos = _extract_videos_from_messages(all_messages)

    return answer, videos, filter_plan

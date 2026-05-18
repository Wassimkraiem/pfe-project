"""LangChain tool-calling agent for video search."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from app.core.config import settings
from app.tools import ALL_VIDEO_TOOLS

logger = logging.getLogger(__name__)
_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
}
_CATEGORY_ALIASES = {
    "animals": "Animals",
    "animal": "Animals",
    "travel": "Travel",
    "travel hotel": "Travel & Hotel",
    "travel and hotel": "Travel & Hotel",
    "hotel": "Travel & Hotel",
    "gym": "Gym",
    "workout": "Gym/Workout",
    "gym workout": "Gym/Workout",
    "food": "Food",
    "comedy": "Comedy",
    "sports": "Sports",
    "beauty": "Beauty",
    "fails": "Fails",
    "weather": "Weather",
    "feels": "Feels",
    "feel good": "Feel good",
    "crafty": "Crafty",
    "diy": "DIY",
    "boozy": "Boozy",
    "cool": "Cool",
}


class VideoSearchFilterPlan(BaseModel):
    method: Literal["auto", "semantic", "filters"] = "auto"
    query: str = ""
    k: int = Field(default=10, ge=1, le=1000)
    sort_by: Literal["relevance", "views", "duration", "newest", "oldest"] = "relevance"
    sort_order: Literal["asc", "desc"] = "desc"
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


def build_agent_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_agent_model,
        temperature=settings.openai_agent_temperature,
    )


def build_video_search_agent(llm: ChatOpenAI, system_prompt: str):
    """Build a LangGraph ReAct agent with video search tools."""
    return create_react_agent(
        model=llm,
        tools=ALL_VIDEO_TOOLS,
        prompt=system_prompt,
    )


def _compact_list(items: list[str]) -> list[str]:
    return [item.strip() for item in items if isinstance(item, str) and item.strip()]


def _has_ranking_intent(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in ("top", "trending", "most viewed", "highest viewed", "viral", "popular")
    )


def _extract_top_k(text: str) -> int | None:
    lowered = text.lower()
    match_num = re.search(r"\btop\s+(\d{1,4})\b", lowered)
    if match_num:
        return int(match_num.group(1))

    match_word = re.search(
        r"\btop\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty)\b",
        lowered,
    )
    if match_word:
        return _NUMBER_WORDS.get(match_word.group(1))
    return None


def _extract_duration_max(text: str) -> float | None:
    lowered = text.lower()
    patterns = (
        r"\bunder\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        r"\bless than\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        r"\bup to\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        r"\bmax(?:imum)?\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        r"\b(\d{1,4})\s*(?:s|sec|secs|second|seconds)\s*(?:max|maximum)?\b",
    )
    for pattern in patterns:
        m = re.search(pattern, lowered)
        if m:
            return float(int(m.group(1)))
    return None


def _extract_categories(text: str) -> list[str]:
    lowered = re.sub(r"[^a-z0-9\s/&-]+", " ", text.lower())
    found: list[str] = []
    for alias, canonical in _CATEGORY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            if canonical not in found:
                found.append(canonical)
    return found


def _normalize_filter_plan(plan: VideoSearchFilterPlan, question: str) -> dict[str, Any]:
    ranking_intent = _has_ranking_intent(question)
    top_k = _extract_top_k(question)
    duration_max_from_text = _extract_duration_max(question)
    categories_from_text = _extract_categories(question)

    normalized_query = plan.query.strip() or question
    if ranking_intent:
        # Ranking intent should not pass a semantic phrase as free-text query.
        normalized_query = ""

    normalized: dict[str, Any] = {
        "method": plan.method,
        "query": normalized_query,
        "k": plan.k,
        "sort_by": plan.sort_by,
        "sort_order": plan.sort_order,
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
    if duration_max_from_text is not None and "duration_max" not in normalized:
        normalized["duration_max"] = duration_max_from_text
    if plan.video_id and plan.video_id.strip():
        normalized["video_id"] = plan.video_id.strip()
        if normalized["method"] == "auto":
            normalized["method"] = "filters"
    if categories_from_text and "categories" not in normalized:
        normalized["categories"] = categories_from_text
    if top_k is not None:
        normalized["k"] = max(1, min(1000, int(top_k)))
    if ranking_intent:
        normalized["sort_by"] = "views"
        normalized["sort_order"] = "desc"
        if normalized["method"] == "auto":
            normalized["method"] = "semantic"
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

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import httpx
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.llm import LLMService

logger = logging.getLogger(__name__)
_CHAT_MAX_RESULTS = 10

_CATEGORY_ALIASES = {
    # Animals
    "animal": "Animals",
    "animals": "Animals",
    "dog": "Animals",
    "dogs": "Animals",
    "cat": "Animals",
    "cats": "Animals",
    "pet": "Animals",
    "pets": "Animals",
    "bird": "Animals",
    "birds": "Animals",
    "wildlife": "Animals",
    # Travel
    "travel": "Travel",
    "hotel": "Travel & Hotel",
    "travel hotel": "Travel & Hotel",
    "tourism": "Travel & Hotel",
    "resort": "Travel & Hotel",
    "sightseeing": "Travel & Hotel",
    # Gym / Workout
    "gym": "Gym/Workout",
    "workout": "Gym/Workout",
    "fitness": "Gym/Workout",
    "exercise": "Gym/Workout",
    "push up": "Gym/Workout",
    "push ups": "Gym/Workout",
    "pushup": "Gym/Workout",
    "pushups": "Gym/Workout",
    "pull up": "Gym/Workout",
    "pull ups": "Gym/Workout",
    "squat": "Gym/Workout",
    "squats": "Gym/Workout",
    "lifting": "Gym/Workout",
    "weightlifting": "Gym/Workout",
    "bodybuilding": "Gym/Workout",
    "crossfit": "Gym/Workout",
    "calisthenics": "Gym/Workout",
    "hiit": "Gym/Workout",
    "yoga": "Gym/Workout",
    "pilates": "Gym/Workout",
    "plank": "Gym/Workout",
    "deadlift": "Gym/Workout",
    "bench press": "Gym/Workout",
    # Sports
    "sports": "Sports",
    "sport": "Sports",
    "football": "Sports",
    "soccer": "Sports",
    "basketball": "Sports",
    "tennis": "Sports",
    "running": "Sports",
    "cycling": "Sports",
    "swimming": "Sports",
    "boxing": "Sports",
    "martial arts": "Sports",
    "skating": "Sports",
    "skateboarding": "Sports",
    "challenge": "Sports",
    "athletic": "Sports",
    # Food
    "food": "Food",
    "cooking": "Food",
    "recipe": "Food",
    "baking": "Food",
    "restaurant": "Food",
    "pasta": "Food",
    "drink": "Food",
    # Comedy
    "comedy": "Comedy",
    "funny": "Comedy",
    "prank": "Comedy",
    "humor": "Comedy",
    "meme": "Comedy",
    # Beauty
    "beauty": "Beauty",
    "makeup": "Beauty",
    "skincare": "Beauty",
    "hair": "Beauty",
    # Fails
    "fails": "Fails",
    "fail": "Fails",
    "blooper": "Fails",
    # Weather
    "weather": "Weather",
    "storm": "Weather",
    "snow": "Weather",
    # DIY / Crafty
    "diy": "DIY",
    "craft": "Crafty",
    "crafty": "Crafty",
    "woodworking": "DIY",
    "knitting": "Crafty",
}

_ORIENTATION_ALIASES = {
    "vertical": "Portrait",
    "portrait": "Portrait",
    "horizontal": "Landscape",
    "landscape": "Landscape",
    "square": "Square",
}

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


class VideoSearchPlan(BaseModel):
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
    limit: int = Field(default=10, ge=1, le=100)


@dataclass(slots=True)
class VideoSearchResult:
    answer: str
    videos: list[dict[str, Any]]
    filters: dict[str, Any]
    search_payload: dict[str, Any]
    total: int | None = None
    next_offset: int | None = None
    execution: dict[str, Any] | None = None
    fallbacks_used: list[str] = field(default_factory=list)


class AdvancedVideoSearchClient:
    def __init__(
        self,
        *,
        base_url: str,
        fallback_urls: str,
        api_key: str,
        timeout_seconds: float,
        retries: int,
    ) -> None:
        self._base_urls = self._dedupe_base_urls(base_url, fallback_urls)
        self._api_key = api_key
        self._retries = max(0, retries)
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds))
        self._facet_cache: dict[str, tuple[float, Any]] = {}
        self._facet_cache_lock = asyncio.Lock()

    @staticmethod
    def _dedupe_base_urls(base_url: str, fallback_urls: str) -> list[str]:
        candidates = [base_url.rstrip("/")]
        candidates.extend(url.strip().rstrip("/") for url in fallback_urls.split(",") if url.strip())
        deduped: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                deduped.append(candidate)
        return deduped

    @classmethod
    def from_settings(cls) -> "AdvancedVideoSearchClient":
        return cls(
            base_url=settings.videos_search_api_url,
            fallback_urls=settings.videos_search_api_fallback_urls,
            api_key=settings.videos_search_api_key,
            timeout_seconds=settings.video_search_timeout_seconds,
            retries=settings.video_search_retries,
        )

    async def close(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", "X-API-KEY": self._api_key}

    async def post_advanced_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request_with_fallback("POST", "/api/videos/advanced-search", json_body=payload)

    async def get_categories(self) -> list[str]:
        body = await self._cached_get("categories", "/api/videos/categories")
        data = body.get("data", body) if isinstance(body, dict) else {}
        categories = data.get("categories", []) if isinstance(data, dict) else []
        return [item for item in categories if isinstance(item, str)]

    async def get_facets(self) -> dict[str, Any]:
        body = await self._cached_get("facets", "/api/videos/facets")
        data = body.get("data", body) if isinstance(body, dict) else {}
        facets = data.get("facets", data) if isinstance(data, dict) else {}
        return facets if isinstance(facets, dict) else {}

    async def _cached_get(self, key: str, path: str) -> dict[str, Any]:
        now = time.monotonic()
        async with self._facet_cache_lock:
            cached = self._facet_cache.get(key)
            if cached and cached[0] > now:
                return cached[1]

        body = await self._request_with_fallback("GET", path)
        async with self._facet_cache_lock:
            self._facet_cache[key] = (now + settings.video_search_facet_cache_ttl_seconds, body)
        return body

    async def _request_with_fallback(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tried: list[str] = []
        last_error = "unknown"

        for base_url in self._base_urls:
            url = f"{base_url}{path}"
            tried.append(base_url)
            for attempt in range(self._retries + 1):
                try:
                    response = await self._client.request(
                        method,
                        url,
                        headers=self._headers(),
                        json=json_body,
                    )
                    response.raise_for_status()
                    parsed = response.json()
                    if isinstance(parsed, dict):
                        return parsed
                    return {"data": parsed}
                except httpx.HTTPStatusError as exc:
                    logger.warning("Video API returned %s for %s", exc.response.status_code, url)
                    return {
                        "error": "http_status_error",
                        "status_code": exc.response.status_code,
                        "message": f"Video search API returned status {exc.response.status_code}.",
                        "base_url": base_url,
                    }
                except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
                    last_error = f"{exc.__class__.__name__}: {exc}"
                    logger.warning("Video API request failed for %s attempt=%s: %s", url, attempt + 1, exc)
                    if attempt < self._retries:
                        await asyncio.sleep(0.15 * (attempt + 1))

        return {
            "error": "connection_error",
            "message": "Unable to connect to the video search API.",
            "details": last_error,
            "tried_base_urls": tried,
        }


class VideoSearchService:
    def __init__(
        self,
        *,
        client: AdvancedVideoSearchClient,
        filter_llm: ChatOpenAI,
        filter_prompt: str,
        llm_service: "LLMService | None" = None,
        query_rewrite_prompt: str = "",
    ) -> None:
        self._client = client
        self._filter_llm = filter_llm
        self._filter_prompt = filter_prompt
        self._llm_service = llm_service
        self._query_rewrite_prompt = query_rewrite_prompt or settings.video_search_query_rewrite_prompt

    async def search(
        self,
        *,
        question: str,
        history_text: str,
        previous_plan: dict[str, Any] | None = None,
        debug: bool = False,
    ) -> VideoSearchResult:
        plan = await self.extract_plan(question=question, history_text=history_text)

        print("\n" + "=" * 60)
        print("[VIDEO SEARCH] Extracted plan")
        print(f"  method   : {plan.method}")
        print(f"  query    : {plan.query!r}")
        print(f"  sort_by  : {plan.sort_by}  sort_order: {plan.sort_order}")
        print(f"  filters  : categories={plan.categories}  tags={plan.tags}  "
              f"orientation={plan.orientation}  resolutions={plan.resolutions}")
        print(f"  duration : min={plan.duration_min}  max={plan.duration_max}")
        print(f"  limit/k  : {plan.limit}/{plan.k}  offset={plan.offset}")
        print("=" * 60)

        if (
            settings.video_search_query_rewriting_enabled
            and self._llm_service is not None
            and plan.query.strip()
        ):
            original_query = plan.query
            plan.query = await self._llm_service.rewrite_video_search_query(
                rewrite_prompt=self._query_rewrite_prompt,
                query=plan.query,
                question=question,
                history_text=history_text,
            )
            print(f"\n[VIDEO SEARCH] Query rewriting")
            print(f"  Before : {original_query!r}")
            print(f"  After  : {plan.query!r}\n")
        else:
            if not plan.query.strip():
                print("\n[VIDEO SEARCH] Query rewriting skipped — ranking-only request (empty query)\n")
            elif not settings.video_search_query_rewriting_enabled:
                print("\n[VIDEO SEARCH] Query rewriting disabled\n")

        normalized = self.normalize_plan(plan, question=question, previous_plan=previous_plan)
        print(f"[VIDEO SEARCH] Normalized payload query: {normalized.get('query')!r}\n")
        payload = self.to_advanced_search_payload(normalized, debug=debug)

        raw_response = await self._client.post_advanced_search(payload)
        if "error" in raw_response:
            return VideoSearchResult(
                answer="I couldn't reach the video search service right now. Please try again in a moment.",
                videos=[],
                filters=normalized,
                search_payload=payload,
                fallbacks_used=[str(raw_response.get("error", "video_api_error"))],
            )

        data = raw_response.get("data", raw_response)
        if not isinstance(data, dict):
            data = {}

        videos = [self._summarize_advanced_item(item) for item in data.get("items", []) if isinstance(item, dict)]
        videos = [video for video in videos if video.get("video_id")]
        total = data.get("total")
        next_offset = data.get("next_offset")
        answer = self._build_answer(videos=videos, total=total)

        return VideoSearchResult(
            answer=answer,
            videos=videos,
            filters=normalized,
            search_payload=payload,
            total=total if isinstance(total, int) else None,
            next_offset=next_offset if isinstance(next_offset, int) else None,
            execution=data.get("execution") if isinstance(data.get("execution"), dict) else None,
            fallbacks_used=data.get("fallbacks_used", []) if isinstance(data.get("fallbacks_used"), list) else [],
        )

    async def extract_plan(self, *, question: str, history_text: str) -> VideoSearchPlan:
        prompt = ChatPromptTemplate.from_template(self._filter_prompt)
        structured_model = self._filter_llm.with_structured_output(VideoSearchPlan)
        chain = prompt | structured_model
        prompt_variables = {
            "history_text": history_text or "No prior messages.",
            "question": question,
        }
        try:
            return await chain.ainvoke(prompt_variables)
        except Exception:
            logger.exception("Video search plan extraction failed")
            return VideoSearchPlan(query=question)

    def normalize_plan(
        self,
        plan: VideoSearchPlan,
        *,
        question: str,
        previous_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        requested_count = self._extract_requested_count(question)
        explicit_show_more = self._is_show_more(question)
        plan_dict = plan.model_dump()
        if self._is_followup(question) and previous_plan:
            merged = dict(previous_plan)
            for key, value in plan_dict.items():
                if self._has_value(value):
                    merged[key] = value
            plan_dict = merged

        query = str(plan_dict.get("query") or "").strip()
        if not query and not self._is_rank_only(question):
            query = question.strip()

        normalized: dict[str, Any] = {
            "method": plan_dict.get("method") or "auto",
            "query": "" if self._is_rank_only(question) else query,
            "k": self._clamp_int(plan_dict.get("k"), default=10, minimum=1, maximum=_CHAT_MAX_RESULTS),
            "sort_by": plan_dict.get("sort_by") or "relevance",
            "sort_order": plan_dict.get("sort_order") or "desc",
            "offset": self._clamp_int(plan_dict.get("offset"), default=0, minimum=0, maximum=100000),
            "limit": self._clamp_int(plan_dict.get("limit"), default=10, minimum=1, maximum=_CHAT_MAX_RESULTS),
        }
        for key in ("categories", "tags", "locations", "resolutions", "orientation"):
            values = [item.strip() for item in plan_dict.get(key, []) if isinstance(item, str) and item.strip()]
            if values:
                normalized[key] = values
        if "categories" not in normalized:
            categories = self._extract_category_aliases(question)
            if categories:
                normalized["categories"] = categories
        if "orientation" not in normalized:
            orientations = self._extract_orientation_aliases(question)
            if orientations:
                normalized["orientation"] = orientations
        if "resolutions" not in normalized:
            resolutions = self._extract_resolutions(question)
            if resolutions:
                normalized["resolutions"] = resolutions
        for key in ("duration_min", "duration_max"):
            value = plan_dict.get(key)
            if isinstance(value, (int, float)):
                normalized[key] = float(value)
        video_id = plan_dict.get("video_id")
        if isinstance(video_id, str) and video_id.strip():
            normalized["video_id"] = video_id.strip()
            normalized["method"] = "filters"

        if self._has_ranking_intent(question):
            normalized["sort_by"] = "views"
            normalized["sort_order"] = "desc"
        if requested_count is not None:
            normalized["k"] = min(requested_count, _CHAT_MAX_RESULTS)
            normalized["limit"] = min(requested_count, _CHAT_MAX_RESULTS)
            if not explicit_show_more:
                normalized["offset"] = 0
        elif self._has_ranking_intent(question) and normalized["k"] != 10 and normalized["limit"] == 10:
            normalized["limit"] = min(normalized["k"], _CHAT_MAX_RESULTS)
        duration_max = self._extract_duration_max(question)
        if duration_max is not None and "duration_max" not in normalized:
            normalized["duration_max"] = duration_max
        if "newest" in question.lower() or "latest" in question.lower():
            normalized["sort_by"] = "newest"
        if "oldest" in question.lower():
            normalized["sort_by"] = "oldest"
        if "shortest" in question.lower():
            normalized["sort_by"] = "duration"
            normalized["sort_order"] = "asc"
        if "longest" in question.lower():
            normalized["sort_by"] = "duration"
            normalized["sort_order"] = "desc"
        if explicit_show_more and previous_plan:
            previous_limit = self._clamp_int(previous_plan.get("limit"), default=10, minimum=1, maximum=_CHAT_MAX_RESULTS)
            previous_offset = self._clamp_int(previous_plan.get("offset"), default=0, minimum=0, maximum=100000)
            normalized["offset"] = previous_offset + previous_limit
            normalized["limit"] = previous_limit

        return normalized

    @staticmethod
    def to_advanced_search_payload(plan: dict[str, Any], *, debug: bool = False) -> dict[str, Any]:
        filters = {
            key: plan[key]
            for key in (
                "categories",
                "tags",
                "locations",
                "resolutions",
                "orientation",
                "duration_min",
                "duration_max",
            )
            if key in plan
        }
        query = plan.get("query", "")
        if not query and plan.get("video_id"):
            query = plan["video_id"]

        return {
            "query": query,
            "filters": filters,
            "sort": {"by": plan.get("sort_by", "relevance"), "order": plan.get("sort_order", "desc")},
            "pagination": {"offset": plan.get("offset", 0), "limit": plan.get("limit", 10)},
            "debug": debug,
        }

    @staticmethod
    def _summarize_advanced_item(item: dict[str, Any]) -> dict[str, Any]:
        document = item.get("document", item)
        if not isinstance(document, dict):
            document = {}
        scores = item.get("scores", {})
        if not isinstance(scores, dict):
            scores = {}

        rms = document.get("rms", {})
        cts = document.get("cts", {})
        rms_data = rms.get("data", {}) if isinstance(rms, dict) else {}
        cts_data = cts.get("data", {}) if isinstance(cts, dict) else {}
        data = rms_data if isinstance(rms_data, dict) and rms_data else cts_data
        additional = data.get("additional", {}) if isinstance(data.get("additional"), dict) else {}
        metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
        default = data.get("default", {}) if isinstance(data.get("default"), dict) else {}

        return {
            "video_id": document.get("video_id") or item.get("video_id", ""),
            "title": document.get("title") or data.get("name") or additional.get("Title", ""),
            "description": (document.get("description") or data.get("description") or additional.get("Description", ""))[:300],
            "tags": document.get("tags") or data.get("tag", []),
            "keywords": document.get("categories") or data.get("keyword", []),
            "views": document.get("views_max") or data.get("views") or 0,
            "duration": document.get("duration_sec") or metadata.get("RDuration"),
            "resolution": document.get("resolution") or default.get("Dimensions", ""),
            "orientation": document.get("orientation") or metadata.get("Orientation", ""),
            "created": document.get("created_ts") or data.get("created") or 0,
            "owner": document.get("owner_name") or data.get("ownerName", ""),
            "thumbnail": data.get("url", {}).get("directUrlPreview", "") if isinstance(data.get("url"), dict) else "",
            "score": scores.get("final") or scores.get("rrf"),
        }

    @staticmethod
    def _build_answer(*, videos: list[dict[str, Any]], total: Any) -> str:
        if not videos:
            return "No matching videos were found. Try broadening the topic or removing some filters."
        count_text = f"{len(videos)} matching videos"
        return f"I found {count_text}. The interface can apply these filters and show the ranked results."

    @staticmethod
    def _has_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict)):
            return bool(value)
        return True

    @staticmethod
    def _clamp_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, min(maximum, parsed))

    @staticmethod
    def _has_ranking_intent(question: str) -> bool:
        lowered = question.lower()
        return any(marker in lowered for marker in ("top", "trending", "most viewed", "highest viewed", "viral", "popular"))

    @staticmethod
    def _extract_requested_count(question: str) -> int | None:
        lowered = question.lower()
        patterns = (
            r"\btop\s+(\d{1,3})\b",
            r"\bshow(?:\s+me)?\s+(\d{1,3})\b",
            r"\b(?:get|give(?:\s+me)?|need|want|return)\s+(?:me\s+)?(\d{1,3})\b",
            r"\bfind\s+(\d{1,3})\b",
            r"\b(\d{1,3})\s+(?:videos|clips|results)\b",
            r"\b(\d{1,3})\s+\w+(?:\s+\w+)?\s+(?:videos|video|clips|results)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return max(1, min(1000, int(match.group(1))))

        word_pattern = (
            r"\btop\s+"
            r"(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
            r"thirteen|fourteen|fifteen|twenty|thirty|forty|fifty)\b"
        )
        match = re.search(word_pattern, lowered)
        if match:
            return _NUMBER_WORDS.get(match.group(1))
        return None

    @staticmethod
    def _is_rank_only(question: str) -> bool:
        lowered = question.lower().strip()
        return lowered in {"top videos", "trending videos", "viral videos", "most viewed videos", "popular videos"}

    @staticmethod
    def _is_followup(question: str) -> bool:
        lowered = question.lower()
        return any(marker in lowered for marker in ("same", "again", "more", "only", "under", "over", "shorter", "longer"))

    @staticmethod
    def _is_show_more(question: str) -> bool:
        lowered = question.lower().strip()
        return lowered in {"more", "show more", "next", "next page", "show me more", "more results"}

    @staticmethod
    def _extract_category_aliases(question: str) -> list[str]:
        lowered = re.sub(r"[^a-z0-9\s/&-]+", " ", question.lower())
        found: list[str] = []
        for alias, canonical in _CATEGORY_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered) and canonical not in found:
                found.append(canonical)
        return found

    @staticmethod
    def _extract_orientation_aliases(question: str) -> list[str]:
        lowered = question.lower()
        found: list[str] = []
        for alias, canonical in _ORIENTATION_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered) and canonical not in found:
                found.append(canonical)
        return found

    @staticmethod
    def _extract_resolutions(question: str) -> list[str]:
        return [match.group(0) for match in re.finditer(r"\b\d{3,4}x\d{3,4}\b", question.lower())]

    @staticmethod
    def _extract_duration_max(question: str) -> float | None:
        lowered = question.lower()
        patterns = (
            r"\bunder\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
            r"\bless than\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
            r"\bup to\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
            r"\bmax(?:imum)?\s+(\d{1,4})\s*(?:s|sec|secs|second|seconds)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return float(match.group(1))
        return None


def safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

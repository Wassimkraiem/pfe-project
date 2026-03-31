"""LangChain tools that wrap the videos-search-api HTTP endpoints."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx
from langchain_core.tools import tool

from app.core.config import settings

logger = logging.getLogger(__name__)
_TIMEOUT = httpx.Timeout(30.0)


def _headers() -> dict[str, str]:
    return {"Content-Type": "application/json", "X-API-KEY": settings.videos_search_api_key}


def _base() -> str:
    return settings.videos_search_api_url.rstrip("/")


def _candidate_bases() -> list[str]:
    candidates = [_base()]
    raw_fallbacks = settings.videos_search_api_fallback_urls
    if raw_fallbacks:
        for item in raw_fallbacks.split(","):
            fallback = item.strip().rstrip("/")
            if fallback:
                candidates.append(fallback)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped


def _extract_video_summary(doc: dict) -> dict:
    """Pull the most useful fields out of a raw OpenSearch video document."""
    video_id = doc.get("video_id", "")

    rms = doc.get("rms", {})
    data = rms.get("data", {}) if isinstance(rms, dict) else {}
    additional = data.get("additional", {})
    metadata = data.get("metadata", {})
    default = data.get("default", {})

    return {
        "video_id": video_id,
        "title": data.get("name") or additional.get("Title", ""),
        "description": (data.get("description") or additional.get("Description", ""))[:300],
        "tags": data.get("tag", []),
        "keywords": data.get("keyword", []),
        "duration": metadata.get("RDuration"),
        "resolution": default.get("Dimensions", ""),
        "orientation": metadata.get("Orientation", ""),
        "owner": data.get("ownerName", ""),
        "thumbnail": data.get("url", {}).get("directUrlPreview", "") if isinstance(data.get("url"), dict) else "",
    }


async def _request_with_fallback(
    method: str,
    path: str,
    *,
    json_body: Any | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tried: list[str] = []
    last_exc: Exception | None = None

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for base in _candidate_bases():
            url = f"{base}{path}"
            tried.append(base)
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=_headers(),
                    json=json_body,
                    params=params,
                )
                response.raise_for_status()
                parsed = response.json()
                if isinstance(parsed, dict):
                    return parsed
                return {"data": parsed}
            except httpx.HTTPStatusError as exc:
                logger.warning("Video API returned status error for %s: %s", url, exc)
                return {
                    "error": "http_status_error",
                    "message": f"Video search API returned status {exc.response.status_code}.",
                    "status_code": exc.response.status_code,
                    "base_url": base,
                }
            except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
                logger.warning("Video API request failed for %s: %s", url, exc)
                last_exc = exc
                continue

    return {
        "error": "connection_error",
        "message": "Unable to connect to the video search API.",
        "details": str(last_exc) if last_exc else "unknown",
        "tried_base_urls": tried,
    }


@tool
async def search_videos_semantic(
    query: str,
    k: int = 10,
    categories: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    duration_min: Optional[float] = None,
    duration_max: Optional[float] = None,
    locations: Optional[list[str]] = None,
    resolutions: Optional[list[str]] = None,
    orientation: Optional[list[str]] = None,
) -> str:
    """Search for videos using semantic (vector) search with optional filters.

    Use this when the user describes what kind of video they want in natural language.
    Returns a JSON object containing matching videos and optional error metadata.

    Args:
        query: Natural-language search query describing the desired videos.
        k: Maximum number of results to return (default 10).
        categories: Optional list of category keywords to filter by.
        tags: Optional list of tags to filter by.
        duration_min: Optional minimum duration in seconds.
        duration_max: Optional maximum duration in seconds.
        locations: Optional list of location strings.
        resolutions: Optional list of resolution strings (e.g. "1920x1080").
        orientation: Optional list of orientation values (e.g. "Landscape").
    """
    payload: dict[str, Any] = {"query": query, "k": k}
    if categories:
        payload["categories"] = categories
    if tags:
        payload["tags"] = tags
    if duration_min is not None:
        payload["duration_min"] = duration_min
    if duration_max is not None:
        payload["duration_max"] = duration_max
    if locations:
        payload["locations"] = locations
    if resolutions:
        payload["resolutions"] = resolutions
    if orientation:
        payload["orientation"] = orientation

    body = await _request_with_fallback("POST", "/api/videos/vsearch", json_body=payload)
    if "error" in body:
        return json.dumps({"videos": [], **body}, ensure_ascii=False)

    data = body.get("data", body)
    raw_docs = data.get("documents", []) if isinstance(data, dict) else []
    videos = [_extract_video_summary(d) for d in raw_docs if isinstance(d, dict)]
    return json.dumps({"videos": videos, "total": len(videos), "query": query}, ensure_ascii=False)


@tool
async def search_videos_by_filters(
    filters: dict,
    offset: int = 0,
    limit: int = 10,
) -> str:
    """Search for videos using exact field filters (term/range queries).

    Use this when the user wants to filter by specific field values rather than free-text.
    Supported filter keys use dot notation, e.g. "rms.keyword" for category.
    Suffix operators: __gte, __lte, __gt, __lt, __in.

    Args:
        filters: A dict mapping field names to values. Example: {"video_id": "abc123"}.
        offset: Pagination offset (default 0).
        limit: Number of results per page (default 10).
    """
    body = await _request_with_fallback(
        "POST",
        "/api/videos/query",
        json_body=filters,
        params={"offset": offset, "limit": limit},
    )
    if "error" in body:
        return json.dumps({"videos": [], "total": 0, "offset": offset, "limit": limit, **body}, ensure_ascii=False)

    data = body.get("data", body)
    raw_videos = data.get("videos", []) if isinstance(data, dict) else []
    videos = [_extract_video_summary(v) for v in raw_videos if isinstance(v, dict)]
    return json.dumps(
        {"videos": videos, "total": data.get("total", len(videos)) if isinstance(data, dict) else len(videos), "offset": offset, "limit": limit},
        ensure_ascii=False,
    )


@tool
async def get_video_categories() -> str:
    """Get all available video categories.

    Use this to discover what categories exist so you can filter searches.
    Returns a JSON list of category name strings.
    """
    body = await _request_with_fallback("GET", "/api/videos/categories")
    if "error" in body:
        return json.dumps({"categories": [], **body}, ensure_ascii=False)

    data = body.get("data", body)
    categories = data.get("categories", []) if isinstance(data, dict) else []
    return json.dumps(categories, ensure_ascii=False)


@tool
async def get_video_facets() -> str:
    """Get available filter facets (locations, durations, resolutions, orientations, tags).

    Use this to discover what filter values are available before applying them.
    Returns a JSON object with lists for each facet dimension.
    """
    body = await _request_with_fallback("GET", "/api/videos/facets")
    if "error" in body:
        return json.dumps({"facets": {}, **body}, ensure_ascii=False)

    data = body.get("data", body)
    facets = data.get("facets", {}) if isinstance(data, dict) else {}
    return json.dumps(facets, ensure_ascii=False)

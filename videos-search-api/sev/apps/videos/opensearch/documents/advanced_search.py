from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests
from flask import g

from sev.apps.videos.opensearch.documents.cache import (
    cache_get,
    cache_set,
    get_ttl,
    is_enabled as cache_is_enabled,
    make_key,
)
from sev.apps.videos.opensearch.documents.services import get_embedding_model

CACHE_KEY_PREFIX = "adv_search:v1"

# Prefer denormalized fields for videos_v2, but keep backward-compatible fallbacks.
LEXICAL_FIELDS = [
    "video_id^4",
    "title^3",
    "description^2",
    "tags^2",
    "categories^2",
    "location",
    "resolution",
    "orientation",
    "owner_name",
    "rms.data.name^2",
    "cts.data.name^2",
    "rms.data.description^2",
    "cts.data.description^2",
    "rms.data.additional.Title^2",
    "cts.data.additional.Title^2",
    "rms.data.additional.Description",
    "cts.data.additional.Description",
    "rms.data.tag",
    "cts.data.tag",
    "rms.data.keyword",
    "cts.data.keyword",
]

STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "for",
    "with",
    "to",
    "in",
    "on",
    "of",
    "video",
    "videos",
}

AMBIGUOUS_MARKERS = {"best", "top", "nice", "good", "cool", "viral", "trending", "popular"}


def _append_fallback(fallbacks: list[str], code: str) -> None:
    if code not in fallbacks:
        fallbacks.append(code)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _current_millis() -> int:
    return int(time.time() * 1000)


def _redact_vectors(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_vectors(item) for key, item in value.items()}
    if isinstance(value, list):
        if value and all(isinstance(item, (int, float)) for item in value):
            return f"<vector length={len(value)}>"
        return [_redact_vectors(item) for item in value]
    return value


def _print_search_query(label: str, payload: dict[str, Any]) -> None:
    try:
        print(f"\n--- {label} ---")
        print(json.dumps(_redact_vectors(payload), ensure_ascii=False, indent=2, default=str))
        print(f"--- End {label} ---\n")
    except Exception as exc:
        print(f"Failed to print {label}: {exc}")


def _normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for item in values:
        if isinstance(item, str):
            value = item.strip()
            if value:
                cleaned.append(value)
    return cleaned


def _normalize_request(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}

    query = payload.get("query")
    query = query.strip() if isinstance(query, str) else ""

    filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}
    normalized_filters = {
        "categories": _normalize_list(filters.get("categories")),
        "tags": _normalize_list(filters.get("tags")),
        "locations": _normalize_list(filters.get("locations")),
        "resolutions": _normalize_list(filters.get("resolutions")),
        "orientation": _normalize_list(filters.get("orientation")),
        "duration_min": filters.get("duration_min") if isinstance(filters.get("duration_min"), (int, float)) else None,
        "duration_max": filters.get("duration_max") if isinstance(filters.get("duration_max"), (int, float)) else None,
        "created_date_start": filters.get("created_date_start") if isinstance(filters.get("created_date_start"), (int, float)) else None,
        "created_date_end": filters.get("created_date_end") if isinstance(filters.get("created_date_end"), (int, float)) else None,
    }

    sort = payload.get("sort") if isinstance(payload.get("sort"), dict) else {}
    sort_by = sort.get("by") if isinstance(sort.get("by"), str) else "relevance"
    sort_order = sort.get("order") if isinstance(sort.get("order"), str) else "desc"
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"

    pagination = payload.get("pagination") if isinstance(payload.get("pagination"), dict) else {}
    offset = pagination.get("offset") if isinstance(pagination.get("offset"), int) else 0
    limit = pagination.get("limit") if isinstance(pagination.get("limit"), int) else 20
    offset = max(0, offset)
    limit = min(max(1, limit), 100)

    strategy = payload.get("strategy") if isinstance(payload.get("strategy"), dict) else {}
    normalized_strategy = {
        "lex_k": max(10, int(strategy.get("lex_k", _env_int("ADVANCED_SEARCH_LEX_K", 120)))),
        "vec_k": max(10, int(strategy.get("vec_k", _env_int("ADVANCED_SEARCH_VEC_K", 120)))),
        "fuse_k": max(10, int(strategy.get("fuse_k", _env_int("ADVANCED_SEARCH_FUSE_K", 150)))),
        "rerank_top_n": max(5, int(strategy.get("rerank_top_n", _env_int("ADVANCED_SEARCH_RERANK_TOP_N", 30)))),
        "rrf_k": max(1, int(strategy.get("rrf_k", _env_int("ADVANCED_SEARCH_RRF_K", 60)))),
        "top_rank_bonus": float(strategy.get("top_rank_bonus", _env_float("ADVANCED_SEARCH_TOP_RANK_BONUS", 0.05))),
        "top_rank_2_3_bonus": float(
            strategy.get("top_rank_2_3_bonus", _env_float("ADVANCED_SEARCH_TOP_RANK_2_3_BONUS", 0.02))
        ),
    }

    debug = bool(payload.get("debug", False))

    return {
        "query": query,
        "filters": normalized_filters,
        "sort": {"by": sort_by, "order": sort_order},
        "pagination": {"offset": offset, "limit": limit},
        "strategy": normalized_strategy,
        "debug": debug,
    }


def _build_filter_clauses(filters: dict[str, Any]) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []

    categories = filters.get("categories", [])
    if categories:
        clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"categories": categories}},
                        {"terms": {"categories.keyword": categories}},
                        {"terms": {"rms.data.keyword.keyword": categories}},
                        {"terms": {"cts.data.keyword.keyword": categories}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    tags = filters.get("tags", [])
    if tags:
        clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"tags": tags}},
                        {"terms": {"tags.keyword": tags}},
                        {"terms": {"rms.data.tag.keyword": tags}},
                        {"terms": {"cts.data.tag.keyword": tags}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    duration_min = filters.get("duration_min")
    duration_max = filters.get("duration_max")
    if duration_min is not None or duration_max is not None:
        rng = {}
        if duration_min is not None:
            rng["gte"] = duration_min
        if duration_max is not None:
            rng["lte"] = duration_max
        clauses.append(
            {
                "bool": {
                    "should": [
                        {"range": {"duration_sec": rng}},
                        {"range": {"rms.data.metadata.RDuration": rng}},
                        {"range": {"cts.data.metadata.RDuration": rng}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    locations = filters.get("locations", [])
    if locations:
        clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"location": locations}},
                        {"terms": {"location.keyword": locations}},
                        {"terms": {"rms.data.additional.Location.keyword": locations}},
                        {"terms": {"cts.data.additional.Location.keyword": locations}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    resolutions = filters.get("resolutions", [])
    if resolutions:
        clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"resolution": resolutions}},
                        {"terms": {"resolution.keyword": resolutions}},
                        {"terms": {"rms.data.default.Dimensions.keyword": resolutions}},
                        {"terms": {"cts.data.default.Dimensions.keyword": resolutions}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    created_start = filters.get("created_date_start")
    created_end = filters.get("created_date_end")
    if created_start is not None or created_end is not None:
        created_range: dict[str, Any] = {}
        if created_start is not None:
            created_range["gte"] = created_start
        if created_end is not None:
            created_range["lte"] = created_end
        clauses.append(
            {
                "bool": {
                    "should": [
                        {"range": {"created_ts": created_range}},
                        {"range": {"created_at": created_range}},
                        {"range": {"rms.data.created": created_range}},
                        {"range": {"cts.data.created": created_range}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    orientations = filters.get("orientation", [])
    if orientations:
        clauses.append(
            {
                "bool": {
                    "should": [
                        {"terms": {"orientation": orientations}},
                        {"terms": {"orientation.keyword": orientations}},
                        {"terms": {"rms.data.metadata.Orientation.keyword": orientations}},
                        {"terms": {"cts.data.metadata.Orientation.keyword": orientations}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        )

    return clauses


def _generate_subqueries(query: str) -> list[dict[str, Any]]:
    if not query:
        return []

    subqueries = [{"query": query, "weight": 2.0, "kind": "original"}]

    tokens = [
        token
        for token in re.findall(r"[\w']+", query.lower())
        if token not in STOP_WORDS and len(token) > 2
    ]
    if tokens:
        expansion = " ".join(tokens[:8])
        if expansion and expansion.lower() != query.lower():
            subqueries.append({"query": expansion, "weight": 1.0, "kind": "expansion"})

    return subqueries


def _search_index_name() -> str:
    return os.environ.get("VIDEOS_READ_ALIAS", "videos_read")


def _existing_search_indices(opensearch_client: Any, fallbacks: list[str]) -> list[str]:
    candidates = [_search_index_name(), "videos"]
    indices: list[str] = []

    for index_name in candidates:
        if index_name in indices:
            continue
        try:
            if opensearch_client.indices.exists(index=index_name):
                indices.append(index_name)
            else:
                _append_fallback(fallbacks, f"search_index_fallback:{index_name}:NotFoundError")
        except Exception as exc:
            _append_fallback(
                fallbacks, f"search_index_fallback:{index_name}:{exc.__class__.__name__}"
            )
    return indices


def _safe_search(
    opensearch_client: Any,
    body: dict[str, Any],
    fallbacks: list[str],
) -> list[dict[str, Any]]:
    indices = _existing_search_indices(opensearch_client, fallbacks)

    for index_name in indices:
        try:
            _print_search_query("OpenSearch search query", {"index": index_name, "body": body})
            response = opensearch_client.search(index=index_name, body=body)
            return response.get("hits", {}).get("hits", [])
        except Exception as exc:
            _append_fallback(
                fallbacks, f"search_index_fallback:{index_name}:{exc.__class__.__name__}"
            )
            continue
    return []


def _lexical_retrieval(
    opensearch_client: Any,
    query: str,
    subqueries: list[dict[str, Any]],
    filters: dict[str, Any],
    limit: int,
    fallbacks: list[str],
) -> list[dict[str, Any]]:
    filter_clauses = _build_filter_clauses(filters)

    should_clauses = []
    if subqueries:
        for sq in subqueries:
            should_clauses.append(
                {
                    "multi_match": {
                        "query": sq["query"],
                        "fields": LEXICAL_FIELDS,
                        "type": "best_fields",
                        "lenient": True,
                        "boost": float(sq["weight"]),
                    }
                }
            )
    elif query:
        should_clauses.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": LEXICAL_FIELDS,
                    "type": "best_fields",
                    "lenient": True,
                }
            }
        )
    else:
        should_clauses.append({"match_all": {}})

    body = {
        "size": limit,
        "query": {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1,
                "filter": filter_clauses,
            }
        },
    }

    return _safe_search(opensearch_client, body, fallbacks)


def _vector_retrieval(
    opensearch_client: Any,
    query: str,
    filters: dict[str, Any],
    limit: int,
    fallbacks: list[str],
) -> list[dict[str, Any]]:
    if not query:
        return []

    model = get_embedding_model()
    if model is None:
        _append_fallback(fallbacks, "vector:embedding_model_unavailable")
        return []

    try:
        vector = model.encode(query).tolist()
    except Exception as exc:
        _append_fallback(fallbacks, f"vector:embedding_failed:{exc.__class__.__name__}")
        return []
    filter_clauses = _build_filter_clauses(filters)
    candidate_indices = _existing_search_indices(opensearch_client, fallbacks)

    if not candidate_indices:
        return []

    vector_field: str | None = None
    target_index: str | None = None
    for index_name in candidate_indices:
        try:
            mapping = opensearch_client.indices.get_mapping(index=index_name)
            # Alias lookups return mappings keyed by the concrete index name, not the alias.
            index_mapping = mapping.get(index_name) or next(iter(mapping.values()), {})
            properties = index_mapping.get("mappings", {}).get("properties", {})
            embedding_def = properties.get("embedding")
            if isinstance(embedding_def, dict) and embedding_def.get("type") == "knn_vector":
                target_index = index_name
                vector_field = "embedding"
                break
            text_vector_def = properties.get("text_vector")
            if isinstance(text_vector_def, dict) and text_vector_def.get("type") == "knn_vector":
                target_index = index_name
                vector_field = "text_vector"
                break
        except Exception as exc:
            _append_fallback(
                fallbacks, f"search_index_fallback:{index_name}:{exc.__class__.__name__}"
            )

    if target_index is None or vector_field is None:
        _append_fallback(fallbacks, "vector:embedding_field_unavailable")
        return []

    body = {
        "size": limit,
        "query": {
            "bool": {
                "must": [
                    {
                        "knn": {
                            vector_field: {
                                "vector": vector,
                                "k": limit,
                            }
                        }
                    }
                ],
                "filter": filter_clauses,
            }
        },
    }
    _print_search_query("OpenSearch vector query", {"index": target_index, "body": body})
    try:
        response = opensearch_client.search(index=target_index, body=body)
    except Exception as exc:
        _append_fallback(
            fallbacks, f"search_index_fallback:{target_index}:{exc.__class__.__name__}"
        )
        return []

    return response.get("hits", {}).get("hits", [])


def _extract_video_id(hit: dict[str, Any]) -> str:
    source = hit.get("_source", {}) if isinstance(hit, dict) else {}
    video_id = source.get("video_id")
    if isinstance(video_id, str):
        return video_id
    return ""


def _fuse_with_rrf(
    lexical_hits: list[dict[str, Any]],
    vector_hits: list[dict[str, Any]],
    rrf_k: int,
    top_rank_bonus: float,
    top_rank_2_3_bonus: float,
) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}

    def rank_bonus(rank: int) -> float:
        if rank == 1:
            return top_rank_bonus
        if rank in {2, 3}:
            return top_rank_2_3_bonus
        return 0.0

    def ensure_candidate(hit: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        video_id = _extract_video_id(hit)
        if not video_id:
            return None
        if video_id not in candidates:
            candidates[video_id] = {
                "video_id": video_id,
                "document": hit.get("_source", {}),
                "scores": {"lex": 0.0, "vec": 0.0, "rrf": 0.0, "rerank": 0.0, "final": 0.0},
            }
        return video_id, candidates[video_id]

    for rank, hit in enumerate(lexical_hits, start=1):
        built = ensure_candidate(hit)
        if built is None:
            continue
        video_id, candidate = built
        raw_score = float(hit.get("_score") or 0.0)
        candidate["scores"]["lex"] = max(candidate["scores"]["lex"], raw_score)
        candidate["scores"]["rrf"] += 1.0 / float(rrf_k + rank)
        candidate["scores"]["rrf"] += rank_bonus(rank)

    for rank, hit in enumerate(vector_hits, start=1):
        built = ensure_candidate(hit)
        if built is None:
            continue
        video_id, candidate = built
        raw_score = float(hit.get("_score") or 0.0)
        candidate["scores"]["vec"] = max(candidate["scores"]["vec"], raw_score)
        candidate["scores"]["rrf"] += 1.0 / float(rrf_k + rank)
        candidate["scores"]["rrf"] += rank_bonus(rank)

    return candidates


def _rerank_with_openai(query: str, candidates: list[dict[str, Any]], fallbacks: list[str]) -> dict[str, float]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        fallbacks.append("rerank:openai_api_key_missing")
        return {}

    model = os.environ.get("OPENAI_RERANK_MODEL", "gpt-4o-mini")
    top_payload = []
    for item in candidates:
        doc = item.get("document", {})
        top_payload.append(
            {
                "video_id": item.get("video_id"),
                "title": doc.get("title") or doc.get("rms", {}).get("data", {}).get("name", ""),
                "description": doc.get("description") or doc.get("rms", {}).get("data", {}).get("description", ""),
                "tags": doc.get("tags") or doc.get("rms", {}).get("data", {}).get("tag", []),
                "categories": doc.get("categories") or doc.get("rms", {}).get("data", {}).get("keyword", []),
            }
        )

    prompt = {
        "query": query,
        "task": "Rank candidate videos by relevance to the query. Return strict JSON array with objects: {video_id, score}. score between 0 and 1.",
        "candidates": top_payload,
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=_env_float("OPENAI_RERANK_TIMEOUT_SECONDS", 2.0),
            json={
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only JSON object with key 'results' containing ranked items.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(prompt),
                    },
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        results = parsed.get("results", []) if isinstance(parsed, dict) else []

        scores: dict[str, float] = {}
        for row in results:
            if not isinstance(row, dict):
                continue
            video_id = row.get("video_id")
            score = row.get("score")
            if isinstance(video_id, str) and isinstance(score, (int, float)):
                scores[video_id] = max(0.0, min(1.0, float(score)))
        return scores
    except Exception as exc:
        fallbacks.append(f"rerank:openai_failed:{exc.__class__.__name__}")
        return {}


def _rerank_heuristic(query: str, candidates: list[dict[str, Any]]) -> dict[str, float]:
    terms = set(re.findall(r"[\w']+", query.lower()))
    if not terms:
        return {}

    scores: dict[str, float] = {}
    for item in candidates:
        doc = item.get("document", {})
        text = " ".join(
            [
                str(doc.get("title", "")),
                str(doc.get("description", "")),
                " ".join(doc.get("tags", []) if isinstance(doc.get("tags"), list) else []),
                " ".join(doc.get("categories", []) if isinstance(doc.get("categories"), list) else []),
            ]
        ).lower()
        text_terms = set(re.findall(r"[\w']+", text))
        if not text_terms:
            scores[item.get("video_id", "")] = 0.0
            continue
        overlap = len(terms.intersection(text_terms)) / float(max(1, len(terms)))
        scores[item.get("video_id", "")] = max(0.0, min(1.0, overlap))
    return scores


def _should_rerank(query: str, sorted_candidates: list[dict[str, Any]]) -> bool:
    if not query or len(sorted_candidates) < 2:
        return False

    text = query.lower()
    is_ambiguous = any(marker in text for marker in AMBIGUOUS_MARKERS)

    top_rrf = float(sorted_candidates[0]["scores"].get("rrf", 0.0))
    second_rrf = float(sorted_candidates[1]["scores"].get("rrf", 0.0))
    confidence_gap = top_rrf - second_rrf

    if is_ambiguous:
        return True
    return confidence_gap < 0.05


def _should_use_openai_rerank(
    query: str,
    sorted_candidates: list[dict[str, Any]],
    heuristic_scores: dict[str, float],
) -> tuple[bool, str]:
    mode = os.environ.get("ADVANCED_SEARCH_OPENAI_RERANK_MODE", "last_resort").strip().lower()
    if mode in {"off", "false", "0", "disabled", "never", "heuristic"}:
        return False, "disabled"
    if not query or len(sorted_candidates) < 2:
        return False, "not_enough_candidates"
    if mode in {"always", "openai"}:
        return True, "mode_always"

    top_rrf = float(sorted_candidates[0]["scores"].get("rrf", 0.0))
    second_rrf = float(sorted_candidates[1]["scores"].get("rrf", 0.0))
    confidence_gap = top_rrf - second_rrf
    max_heuristic = max(heuristic_scores.values(), default=0.0)
    top_has_lexical = any(float(item["scores"].get("lex", 0.0)) > 0 for item in sorted_candidates[:5])
    top_has_vector = any(float(item["scores"].get("vec", 0.0)) > 0 for item in sorted_candidates[:5])

    weak_gap_threshold = _env_float("ADVANCED_SEARCH_OPENAI_RERANK_WEAK_GAP", 0.015)
    weak_heuristic_threshold = _env_float("ADVANCED_SEARCH_OPENAI_RERANK_WEAK_HEURISTIC", 0.10)
    min_candidates = _env_int("ADVANCED_SEARCH_OPENAI_RERANK_MIN_CANDIDATES", 8)

    if len(sorted_candidates) < min_candidates:
        return False, "local_candidate_count_ok"
    if not top_has_lexical and not top_has_vector:
        return True, "no_local_signal"
    if confidence_gap <= weak_gap_threshold and max_heuristic <= weak_heuristic_threshold:
        return True, "weak_local_confidence"
    return False, "local_confident"


def _apply_position_aware_blend(
    candidates: list[dict[str, Any]],
    rerank_scores: dict[str, float],
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    rrf_values = [float(c["scores"].get("rrf", 0.0)) for c in candidates]
    min_rrf = min(rrf_values)
    max_rrf = max(rrf_values)
    denom = max(max_rrf - min_rrf, 1e-9)

    for idx, candidate in enumerate(candidates):
        retrieval_norm = (float(candidate["scores"].get("rrf", 0.0)) - min_rrf) / denom
        rerank = float(rerank_scores.get(candidate["video_id"], 0.0))
        candidate["scores"]["rerank"] = rerank

        if idx < 5:
            retrieval_weight = 0.8
        elif idx < 15:
            retrieval_weight = 0.6
        else:
            retrieval_weight = 0.4

        final_score = (retrieval_weight * retrieval_norm) + ((1.0 - retrieval_weight) * rerank)
        candidate["scores"]["final"] = final_score

    return sorted(candidates, key=lambda item: float(item["scores"].get("final", 0.0)), reverse=True)


def _build_sort(items: list[dict[str, Any]], sort_by: str, sort_order: str) -> list[dict[str, Any]]:
    if sort_by == "relevance":
        return items

    reverse = sort_order != "asc"

    def pick_numeric(doc: dict[str, Any], *paths: str) -> float:
        for path in paths:
            current = doc
            ok = True
            for part in path.split("."):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    ok = False
                    break
            if ok and isinstance(current, (int, float)):
                return float(current)
        return 0.0

    if sort_by == "views":
        return sorted(
            items,
            key=lambda item: max(
                pick_numeric(item["document"], "views_max"),
                pick_numeric(item["document"], "rms.data.views"),
                pick_numeric(item["document"], "cts.data.views"),
            ),
            reverse=reverse,
        )

    if sort_by == "newest":
        return sorted(
            items,
            key=lambda item: max(
                pick_numeric(item["document"], "created_ts"),
                pick_numeric(item["document"], "created_at"),
                pick_numeric(item["document"], "rms.data.created"),
                pick_numeric(item["document"], "cts.data.created"),
            ),
            reverse=True,
        )

    if sort_by == "oldest":
        return sorted(
            items,
            key=lambda item: max(
                pick_numeric(item["document"], "created_ts"),
                pick_numeric(item["document"], "created_at"),
                pick_numeric(item["document"], "rms.data.created"),
                pick_numeric(item["document"], "cts.data.created"),
            ),
            reverse=False,
        )

    if sort_by == "duration":
        return sorted(
            items,
            key=lambda item: max(
                pick_numeric(item["document"], "duration_sec"),
                pick_numeric(item["document"], "rms.data.metadata.RDuration"),
                pick_numeric(item["document"], "cts.data.metadata.RDuration"),
            ),
            reverse=reverse,
        )

    return items


def advanced_search(payload: dict[str, Any]) -> dict[str, Any]:
    execution: dict[str, int] = {}
    started = _current_millis()
    fallbacks_used: list[str] = []
    opensearch_client = g.video_opensearch

    stage_started = _current_millis()
    normalized = _normalize_request(payload)
    execution["normalize_ms"] = _current_millis() - stage_started
    _print_search_query("Advanced search request", normalized)

    cache_enabled = cache_is_enabled()
    cache_key: str | None = None
    if cache_enabled:
        cache_payload = {k: v for k, v in normalized.items() if k != "debug"}
        cache_key = make_key(CACHE_KEY_PREFIX, cache_payload)
        cache_lookup_started = _current_millis()
        cached = cache_get(cache_key)
        if cached is not None:
            cached_response = dict(cached)
            cached_execution = dict(cached_response.get("execution", {}))
            cached_execution["normalize_ms"] = execution["normalize_ms"]
            cached_execution["cache_lookup_ms"] = _current_millis() - cache_lookup_started
            cached_execution["total_ms"] = _current_millis() - started
            cached_response["execution"] = cached_execution
            cached_response["cache"] = {"hit": True, "key": cache_key}
            if normalized["debug"]:
                cached_response["debug"] = {
                    "normalized_request": normalized,
                    "cache": {"hit": True, "key": cache_key},
                }
            return cached_response

    stage_started = _current_millis()
    subqueries = _generate_subqueries(normalized["query"])
    execution["subquery_ms"] = _current_millis() - stage_started

    stage_started = _current_millis()
    with ThreadPoolExecutor(max_workers=2) as executor:
        lexical_future = executor.submit(
            _lexical_retrieval,
            opensearch_client=opensearch_client,
            query=normalized["query"],
            subqueries=subqueries,
            filters=normalized["filters"],
            limit=normalized["strategy"]["lex_k"],
            fallbacks=fallbacks_used,
        )
        vector_future = executor.submit(
            _vector_retrieval,
            opensearch_client=opensearch_client,
            query=normalized["query"],
            filters=normalized["filters"],
            limit=normalized["strategy"]["vec_k"],
            fallbacks=fallbacks_used,
        )
        lexical_hits = lexical_future.result()
        vector_hits = vector_future.result()
    execution["retrieval_ms"] = _current_millis() - stage_started

    stage_started = _current_millis()
    fused = _fuse_with_rrf(
        lexical_hits=lexical_hits,
        vector_hits=vector_hits,
        rrf_k=normalized["strategy"]["rrf_k"],
        top_rank_bonus=normalized["strategy"]["top_rank_bonus"],
        top_rank_2_3_bonus=normalized["strategy"]["top_rank_2_3_bonus"],
    )
    fused_items = sorted(
        fused.values(),
        key=lambda item: float(item["scores"].get("rrf", 0.0)),
        reverse=True,
    )[: normalized["strategy"]["fuse_k"]]
    execution["fusion_ms"] = _current_millis() - stage_started

    stage_started = _current_millis()
    rerank_candidates = fused_items[: normalized["strategy"]["rerank_top_n"]]
    rerank_scores: dict[str, float] = {}
    rerank_source = "none"
    openai_rerank_reason = "not_considered"
    if _should_rerank(normalized["query"], rerank_candidates):
        rerank_scores = _rerank_heuristic(normalized["query"], rerank_candidates)
        rerank_source = "heuristic" if rerank_scores else "none"
        should_use_openai, openai_rerank_reason = _should_use_openai_rerank(
            normalized["query"],
            rerank_candidates,
            rerank_scores,
        )
        if should_use_openai:
            _append_fallback(fallbacks_used, f"rerank:openai_last_resort:{openai_rerank_reason}")
            openai_scores = _rerank_with_openai(normalized["query"], rerank_candidates, fallbacks_used)
            if openai_scores:
                rerank_scores = openai_scores
                rerank_source = "openai_last_resort"
            elif rerank_scores:
                rerank_source = "heuristic_after_openai_failure"
            else:
                _append_fallback(fallbacks_used, "rerank:heuristic_unavailable")
    execution["rerank_ms"] = _current_millis() - stage_started

    stage_started = _current_millis()
    blended = _apply_position_aware_blend(fused_items, rerank_scores)
    sorted_items = _build_sort(blended, normalized["sort"]["by"], normalized["sort"]["order"])
    execution["blend_ms"] = _current_millis() - stage_started

    offset = normalized["pagination"]["offset"]
    limit = normalized["pagination"]["limit"]
    page = sorted_items[offset : offset + limit]
    total = len(sorted_items)
    next_offset = offset + limit if (offset + limit) < total else None

    execution["total_ms"] = _current_millis() - started

    response = {
        "items": page,
        "total": total,
        "next_offset": next_offset,
        "applied_filters": normalized["filters"],
        "execution": execution,
        "fallbacks_used": fallbacks_used,
    }

    if cache_enabled and cache_key:
        cacheable = {k: v for k, v in response.items()}
        cache_set(cache_key, cacheable, ttl=get_ttl())
        response["cache"] = {"hit": False, "key": cache_key}
    else:
        response["cache"] = {"hit": False, "key": None}

    if normalized["debug"]:
        response["debug"] = {
            "normalized_request": normalized,
            "subqueries": subqueries,
            "retrieval_counts": {
                "lexical": len(lexical_hits),
                "vector": len(vector_hits),
                "fused": len(fused_items),
            },
            "rerank": {
                "source": rerank_source,
                "openai_reason": openai_rerank_reason,
                "candidate_count": len(rerank_candidates),
            },
        }

    return response

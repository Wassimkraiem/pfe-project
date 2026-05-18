from __future__ import annotations

import json
import math
import os
import statistics
import time
from pathlib import Path
from typing import Any

import pytest
import requests


API_URL = os.getenv("SEARCH_API_URL", "http://127.0.0.1:5000").rstrip("/")
API_KEY = os.getenv("SEARCH_API_KEY", "key1")
DATASET_PATH = Path(
    os.getenv(
        "SEARCH_EVAL_DATASET",
        str(Path(__file__).resolve().parent / "search_eval_dataset.json"),
    )
)
DEFAULT_K = int(os.getenv("SEARCH_EVAL_K", "20"))

# Optional pass/fail thresholds (unset = report-only)
MIN_ADV_NDCG = os.getenv("SEARCH_EVAL_MIN_ADV_NDCG")
MIN_NDCG_LIFT = os.getenv("SEARCH_EVAL_MIN_NDCG_LIFT")
MAX_ADV_P95_MS = os.getenv("SEARCH_EVAL_MAX_ADV_P95_MS")


def _as_float_or_none(raw: str | None) -> float | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    return float(value)


MIN_ADV_NDCG_VALUE = _as_float_or_none(MIN_ADV_NDCG)
MIN_NDCG_LIFT_VALUE = _as_float_or_none(MIN_NDCG_LIFT)
MAX_ADV_P95_MS_VALUE = _as_float_or_none(MAX_ADV_P95_MS)


def _load_dataset() -> list[dict[str, Any]]:
    if not DATASET_PATH.exists():
        pytest.skip(
            f"Dataset not found at {DATASET_PATH}. Copy search_eval_dataset.example.json to search_eval_dataset.json and fill judged relevance IDs."
        )

    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    queries = payload.get("queries", []) if isinstance(payload, dict) else []
    if not isinstance(queries, list) or not queries:
        pytest.skip("Dataset has no queries. Populate `queries` with judged relevance entries.")

    normalized: list[dict[str, Any]] = []
    for row in queries:
        if not isinstance(row, dict):
            continue
        query_text = row.get("query", "")
        if not isinstance(query_text, str) or not query_text.strip():
            continue

        judged = row.get("relevant", [])
        judged_map: dict[str, int] = {}
        if isinstance(judged, list):
            for item in judged:
                if not isinstance(item, dict):
                    continue
                vid = item.get("video_id")
                grade = item.get("grade", 0)
                if isinstance(vid, str) and vid.strip() and isinstance(grade, (int, float)):
                    judged_map[vid.strip()] = int(grade)

        normalized.append(
            {
                "id": row.get("id") or f"q{len(normalized) + 1}",
                "query": query_text.strip(),
                "filters": row.get("filters", {}) if isinstance(row.get("filters"), dict) else {},
                "k": int(row.get("k", DEFAULT_K)),
                "judged": judged_map,
            }
        )

    if not normalized:
        pytest.skip("Dataset queries are invalid/empty after normalization.")
    return normalized


def _discount(rank: int) -> float:
    return 1.0 / math.log2(rank + 1)


def _ndcg_at_k(ranked_ids: list[str], judged: dict[str, int], k: int) -> float:
    dcg = 0.0
    for i, vid in enumerate(ranked_ids[:k], start=1):
        rel = max(0, judged.get(vid, 0))
        if rel > 0:
            dcg += (2**rel - 1) * _discount(i)

    ideal_rels = sorted((g for g in judged.values() if g > 0), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_rels, start=1):
        idcg += (2**rel - 1) * _discount(i)

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def _mrr_at_k(ranked_ids: list[str], judged: dict[str, int], k: int) -> float:
    for i, vid in enumerate(ranked_ids[:k], start=1):
        if judged.get(vid, 0) > 0:
            return 1.0 / i
    return 0.0


def _recall_at_k(ranked_ids: list[str], judged: dict[str, int], k: int) -> float:
    relevant_ids = {vid for vid, grade in judged.items() if grade > 0}
    if not relevant_ids:
        return 0.0
    found = set(ranked_ids[:k]).intersection(relevant_ids)
    return len(found) / len(relevant_ids)


def _precision_at_k(ranked_ids: list[str], judged: dict[str, int], k: int) -> float:
    if k <= 0:
        return 0.0
    top = ranked_ids[:k]
    if not top:
        return 0.0
    good = sum(1 for vid in top if judged.get(vid, 0) > 0)
    return good / k


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1))
    return ordered[idx]


def _extract_ids_from_vsearch(data: dict[str, Any]) -> list[str]:
    docs = data.get("documents", []) if isinstance(data, dict) else []
    ids: list[str] = []
    if isinstance(docs, list):
        for item in docs:
            if isinstance(item, dict):
                vid = item.get("video_id")
                if isinstance(vid, str) and vid:
                    ids.append(vid)
    return ids


def _extract_ids_from_advanced(data: dict[str, Any]) -> list[str]:
    items = data.get("items", []) if isinstance(data, dict) else []
    ids: list[str] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            vid = item.get("video_id")
            if isinstance(vid, str) and vid:
                ids.append(vid)
    return ids


def _call_vsearch(query: str, filters: dict[str, Any], k: int) -> tuple[list[str], float, float]:
    payload: dict[str, Any] = {"query": query, "k": k}
    for key in (
        "categories",
        "tags",
        "duration_min",
        "duration_max",
        "locations",
        "resolutions",
        "orientation",
        "sort_by",
        "sort_order",
    ):
        if key in filters:
            payload[key] = filters[key]

    started = time.perf_counter()
    try:
        res = requests.post(
            f"{API_URL}/api/videos/vsearch",
            headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        pytest.skip(f"vsearch endpoint unreachable: {exc}")
    client_ms = (time.perf_counter() - started) * 1000.0
    if res.status_code >= 400:
        snippet = res.text[:400]
        pytest.skip(f"vsearch returned HTTP {res.status_code}: {snippet}")

    body = res.json()
    data = body.get("data", {}) if isinstance(body, dict) else {}
    execution = data.get("execution", {}) if isinstance(data, dict) else {}
    server_ms = float(execution.get("total_ms", 0.0) or 0.0)
    return _extract_ids_from_vsearch(data), server_ms, client_ms


def _call_advanced(query: str, filters: dict[str, Any], k: int) -> tuple[list[str], float, float]:
    payload = {
        "query": query,
        "filters": {
            "categories": filters.get("categories", []),
            "tags": filters.get("tags", []),
            "locations": filters.get("locations", []),
            "resolutions": filters.get("resolutions", []),
            "orientation": filters.get("orientation", []),
            "duration_min": filters.get("duration_min"),
            "duration_max": filters.get("duration_max"),
        },
        "sort": {
            "by": filters.get("sort_by", "relevance"),
            "order": filters.get("sort_order", "desc"),
        },
        "pagination": {"offset": 0, "limit": k},
    }

    started = time.perf_counter()
    try:
        res = requests.post(
            f"{API_URL}/api/videos/advanced-search",
            headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        pytest.skip(f"advanced-search endpoint unreachable: {exc}")
    client_ms = (time.perf_counter() - started) * 1000.0
    if res.status_code >= 400:
        snippet = res.text[:400]
        pytest.skip(f"advanced-search returned HTTP {res.status_code}: {snippet}")

    body = res.json()
    data = body.get("data", {}) if isinstance(body, dict) else {}
    execution = data.get("execution", {}) if isinstance(data, dict) else {}
    server_ms = float(execution.get("total_ms", 0.0) or 0.0)
    return _extract_ids_from_advanced(data), server_ms, client_ms


def _aggregate(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "p95": 0.0}
    return {
        "mean": float(statistics.mean(values)),
        "p95": float(_p95(values)),
    }


def test_search_accuracy_and_speed_benchmark():
    queries = _load_dataset()

    ndcg_v: list[float] = []
    mrr_v: list[float] = []
    recall_v: list[float] = []
    precision_v: list[float] = []
    server_v: list[float] = []
    client_v: list[float] = []

    ndcg_a: list[float] = []
    mrr_a: list[float] = []
    recall_a: list[float] = []
    precision_a: list[float] = []
    server_a: list[float] = []
    client_a: list[float] = []

    per_query: list[dict[str, Any]] = []

    for item in queries:
        judged = item["judged"]
        k = max(1, int(item["k"]))

        v_ids, v_server_ms, v_client_ms = _call_vsearch(item["query"], item["filters"], k)
        a_ids, a_server_ms, a_client_ms = _call_advanced(item["query"], item["filters"], k)

        ndcg_v_q = _ndcg_at_k(v_ids, judged, min(10, k))
        mrr_v_q = _mrr_at_k(v_ids, judged, min(10, k))
        recall_v_q = _recall_at_k(v_ids, judged, min(20, k))
        precision_v_q = _precision_at_k(v_ids, judged, min(10, k))

        ndcg_a_q = _ndcg_at_k(a_ids, judged, min(10, k))
        mrr_a_q = _mrr_at_k(a_ids, judged, min(10, k))
        recall_a_q = _recall_at_k(a_ids, judged, min(20, k))
        precision_a_q = _precision_at_k(a_ids, judged, min(10, k))

        ndcg_v.append(ndcg_v_q)
        mrr_v.append(mrr_v_q)
        recall_v.append(recall_v_q)
        precision_v.append(precision_v_q)
        server_v.append(v_server_ms)
        client_v.append(v_client_ms)

        ndcg_a.append(ndcg_a_q)
        mrr_a.append(mrr_a_q)
        recall_a.append(recall_a_q)
        precision_a.append(precision_a_q)
        server_a.append(a_server_ms)
        client_a.append(a_client_ms)

        per_query.append(
            {
                "id": item["id"],
                "query": item["query"],
                "vsearch": {
                    "ndcg@10": ndcg_v_q,
                    "mrr@10": mrr_v_q,
                    "recall@20": recall_v_q,
                    "precision@10": precision_v_q,
                    "server_ms": v_server_ms,
                    "client_ms": round(v_client_ms, 2),
                },
                "advanced": {
                    "ndcg@10": ndcg_a_q,
                    "mrr@10": mrr_a_q,
                    "recall@20": recall_a_q,
                    "precision@10": precision_a_q,
                    "server_ms": a_server_ms,
                    "client_ms": round(a_client_ms, 2),
                },
            }
        )

    summary = {
        "dataset": str(DATASET_PATH),
        "queries": len(queries),
        "vsearch": {
            "accuracy": {
                "ndcg@10": float(statistics.mean(ndcg_v)),
                "mrr@10": float(statistics.mean(mrr_v)),
                "recall@20": float(statistics.mean(recall_v)),
                "precision@10": float(statistics.mean(precision_v)),
            },
            "speed": {
                "server_ms": _aggregate(server_v),
                "client_ms": _aggregate(client_v),
            },
        },
        "advanced_search": {
            "accuracy": {
                "ndcg@10": float(statistics.mean(ndcg_a)),
                "mrr@10": float(statistics.mean(mrr_a)),
                "recall@20": float(statistics.mean(recall_a)),
                "precision@10": float(statistics.mean(precision_a)),
            },
            "speed": {
                "server_ms": _aggregate(server_a),
                "client_ms": _aggregate(client_a),
            },
        },
        "delta_advanced_minus_vsearch": {
            "ndcg@10": float(statistics.mean(ndcg_a) - statistics.mean(ndcg_v)),
            "mrr@10": float(statistics.mean(mrr_a) - statistics.mean(mrr_v)),
            "recall@20": float(statistics.mean(recall_a) - statistics.mean(recall_v)),
            "precision@10": float(statistics.mean(precision_a) - statistics.mean(precision_v)),
            "server_mean_ms": float(statistics.mean(server_a) - statistics.mean(server_v)),
            "server_p95_ms": float(_p95(server_a) - _p95(server_v)),
        },
        "per_query": per_query,
    }

    print("\n=== Search Accuracy/Speed Benchmark ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    assert len(queries) > 0
    assert summary["vsearch"]["speed"]["server_ms"]["mean"] >= 0
    assert summary["advanced_search"]["speed"]["server_ms"]["mean"] >= 0

    if MIN_ADV_NDCG_VALUE is not None:
        assert summary["advanced_search"]["accuracy"]["ndcg@10"] >= MIN_ADV_NDCG_VALUE

    if MIN_NDCG_LIFT_VALUE is not None:
        assert summary["delta_advanced_minus_vsearch"]["ndcg@10"] >= MIN_NDCG_LIFT_VALUE

    if MAX_ADV_P95_MS_VALUE is not None:
        assert summary["advanced_search"]["speed"]["server_ms"]["p95"] <= MAX_ADV_P95_MS_VALUE

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from opensearchpy import OpenSearch, RequestsHttpConnection, helpers

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill OpenSearch video documents with 1536-dimension embeddings."
    )
    parser.add_argument("--source-index", default="videos")
    parser.add_argument("--dest-index", default=os.getenv("VIDEOS_INDEX_NAME", "videos_v2_1536"))
    parser.add_argument("--read-alias", default=os.getenv("VIDEOS_READ_ALIAS", "videos_read"))
    parser.add_argument("--write-alias", default=os.getenv("VIDEOS_WRITE_ALIAS", "videos_write"))
    parser.add_argument("--embedding-model", default=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    parser.add_argument("--embedding-dimension", type=int, default=int(os.getenv("EMBEDDING_DIMENSION", "1536")))
    parser.add_argument("--scroll-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--reset-dest", action="store_true", help="Delete and recreate destination index first.")
    parser.add_argument("--switch-aliases", action="store_true", help="Point read/write aliases to dest after backfill.")
    parser.add_argument("--dry-run", action="store_true", help="Read and build payloads without indexing.")
    return parser.parse_args()


def build_videos_v2_mapping(embedding_dimension: int = 1536) -> dict[str, Any]:
    return {
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "video_id": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "description": {"type": "text"},
                "tags": {"type": "keyword"},
                "categories": {"type": "keyword"},
                "duration_sec": {"type": "float"},
                "location": {"type": "keyword"},
                "resolution": {"type": "keyword"},
                "orientation": {"type": "keyword"},
                "views_max": {"type": "long"},
                "created_ts": {"type": "long"},
                "owner_name": {"type": "keyword"},
                "embedding": {"type": "knn_vector", "dimension": embedding_dimension},
                "raw": {"type": "object", "enabled": False},
                "rms": {"type": "object", "enabled": False},
                "cts": {"type": "object", "enabled": False},
            }
        },
    }


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
        return parts or [value.strip()]
    return [str(value).strip()] if str(value).strip() else []


def first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def int_or_none(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def build_video_embedding_text(video_data: dict[str, Any]) -> str:
    additional = video_data.get("additional") if isinstance(video_data.get("additional"), dict) else {}
    tokens = [
        first_text(video_data.get("title"), video_data.get("name"), additional.get("Title")),
        first_text(video_data.get("description"), additional.get("Description")),
        " ".join(as_list(video_data.get("tag") or video_data.get("tags"))),
        " ".join(as_list(video_data.get("keyword") or video_data.get("category") or video_data.get("categories"))),
        first_text(video_data.get("location"), additional.get("Location")),
        first_text(video_data.get("ownerName"), video_data.get("owner_name")),
    ]
    text = " ".join(token for token in tokens if token).strip()
    return text or "default"


def build_video_denormalized_fields(video_data: dict[str, Any]) -> dict[str, Any]:
    metadata = video_data.get("metadata") if isinstance(video_data.get("metadata"), dict) else {}
    default = video_data.get("default") if isinstance(video_data.get("default"), dict) else {}
    additional = video_data.get("additional") if isinstance(video_data.get("additional"), dict) else {}
    return {
        "title": first_text(video_data.get("title"), video_data.get("name"), additional.get("Title")),
        "description": first_text(video_data.get("description"), additional.get("Description")),
        "tags": as_list(video_data.get("tag") or video_data.get("tags")),
        "categories": as_list(video_data.get("keyword") or video_data.get("category") or video_data.get("categories")),
        "duration_sec": float_or_none(
            video_data.get("duration") or metadata.get("duration") or metadata.get("RDuration")
        ),
        "location": first_text(video_data.get("location"), additional.get("Location")),
        "resolution": first_text(video_data.get("resolution"), default.get("Dimensions")),
        "orientation": first_text(video_data.get("orientation"), metadata.get("Orientation")),
        "views_max": int_or_none(video_data.get("views") or video_data.get("views_max")),
        "created_ts": int_or_none(video_data.get("created") or video_data.get("created_ts")),
        "owner_name": first_text(video_data.get("ownerName"), video_data.get("owner_name")),
        "raw": video_data,
    }


def build_opensearch_client() -> OpenSearch:
    host = os.getenv("OPENSEARCH_HOST", "localhost")
    port = int(os.getenv("OPENSEARCH_PORT", "9200"))
    user = os.getenv("OPENSEARCH_AUTH_ADMIN", "")
    password = os.getenv("OPENSEARCH_INITIAL_ADMIN_PASSWORD", "")
    http_auth = (user, password) if user or password else None
    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=http_auth,
        use_ssl=False,
        connection_class=RequestsHttpConnection,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=60,
        max_retries=3,
        retry_on_timeout=True,
    )


def ensure_dest_index(client: OpenSearch, index_name: str, dimension: int, reset: bool) -> None:
    exists = client.indices.exists(index=index_name)
    if exists and reset:
        client.indices.delete(index=index_name)
        exists = False
    if not exists:
        client.indices.create(index=index_name, body=build_videos_v2_mapping(embedding_dimension=dimension))


def service_payloads(source: dict[str, Any]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    raw = source.get("raw")
    if isinstance(raw, dict):
        payloads.append(raw)
    video_data = source.get("video_data")
    if isinstance(video_data, dict):
        payloads.append(video_data)
    for value in source.values():
        if not isinstance(value, dict):
            continue
        data = value.get("data")
        if isinstance(data, dict):
            payloads.append(data)
    if not payloads:
        payloads.append(source)
    return payloads


def merged_payload(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for payload in payloads:
        merged.update(payload)
    return merged


def embedding_text_for_source(source: dict[str, Any]) -> str:
    texts = [build_video_embedding_text(payload) for payload in service_payloads(source)]
    combined = " ".join(text for text in texts if text and text != "default").strip()
    return combined or "default"


def build_destination_doc(source: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
    payloads = service_payloads(source)
    merged = merged_payload(payloads)
    doc = {
        key: value
        for key, value in source.items()
        if key not in {"text_vector", "embedding"} and value not in (None, "", [])
    }
    doc.update(
        {
            key: value
            for key, value in build_video_denormalized_fields(merged).items()
            if value not in (None, "", [])
        }
    )
    doc["embedding"] = embedding
    return doc


def embed_batch(client: OpenAI, model: str, dimension: int, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=model, input=texts, dimensions=dimension)
    vectors = [item.embedding for item in response.data]
    for vector in vectors:
        if len(vector) != dimension:
            raise RuntimeError(f"Embedding dimension mismatch: got {len(vector)}, expected {dimension}")
    return vectors


def switch_aliases(client: OpenSearch, index_name: str, read_alias: str, write_alias: str) -> None:
    actions: list[dict[str, Any]] = []
    for alias_name in (read_alias, write_alias):
        try:
            for old_index in client.indices.get_alias(name=alias_name).keys():
                actions.append({"remove": {"index": old_index, "alias": alias_name}})
        except Exception:
            pass
    actions.extend(
        [
            {"add": {"index": index_name, "alias": read_alias}},
            {"add": {"index": index_name, "alias": write_alias, "is_write_index": True}},
        ]
    )
    client.indices.update_aliases(body={"actions": actions})


def main() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parent / "agentic-helper" / ".env")
    args = parse_args()
    os_client = build_opensearch_client()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    ensure_dest_index(os_client, args.dest_index, args.embedding_dimension, args.reset_dest)

    processed = embedded = indexed = failed = 0
    started = time.time()
    batch: list[dict[str, Any]] = []

    for hit in helpers.scan(
        os_client,
        index=args.source_index,
        query={"query": {"match_all": {}}},
        size=args.scroll_size,
        preserve_order=False,
    ):
        if args.limit is not None and processed >= args.limit:
            break
        batch.append(hit)
        if len(batch) >= args.batch_size:
            result = process_batch(os_client, openai_client, args, batch)
            embedded += result["embedded"]
            indexed += result["indexed"]
            failed += result["failed"]
            processed += len(batch)
            print_progress(processed, embedded, indexed, failed, started)
            batch = []

    if batch:
        result = process_batch(os_client, openai_client, args, batch)
        embedded += result["embedded"]
        indexed += result["indexed"]
        failed += result["failed"]
        processed += len(batch)
        print_progress(processed, embedded, indexed, failed, started)

    if args.switch_aliases and not args.dry_run:
        switch_aliases(os_client, args.dest_index, args.read_alias, args.write_alias)
        print(f"Switched {args.read_alias}/{args.write_alias} to {args.dest_index}.")

    print_progress(processed, embedded, indexed, failed, started, final=True)
    return 1 if failed else 0


def process_batch(
    os_client: OpenSearch,
    openai_client: OpenAI,
    args: argparse.Namespace,
    hits: list[dict[str, Any]],
) -> dict[str, int]:
    texts = [embedding_text_for_source(hit.get("_source", {})) for hit in hits]
    try:
        vectors = embed_batch(openai_client, args.embedding_model, args.embedding_dimension, texts)
    except Exception as exc:
        print(f"Embedding batch failed: {exc}", file=sys.stderr)
        return {"embedded": 0, "indexed": 0, "failed": len(hits)}

    actions = []
    for hit, vector in zip(hits, vectors):
        source = hit.get("_source", {})
        actions.append(
            {
                "_op_type": "index",
                "_index": args.dest_index,
                "_id": hit.get("_id") or source.get("video_id"),
                "_source": build_destination_doc(source, vector),
            }
        )

    if args.dry_run:
        return {"embedded": len(vectors), "indexed": 0, "failed": 0}

    success, errors = helpers.bulk(os_client, actions, refresh=False, raise_on_error=False)
    if errors:
        print(f"First bulk error: {errors[0]}", file=sys.stderr)
    return {"embedded": len(vectors), "indexed": success, "failed": len(errors)}


def print_progress(
    processed: int,
    embedded: int,
    indexed: int,
    failed: int,
    started: float,
    *,
    final: bool = False,
) -> None:
    label = "FINAL" if final else "progress"
    elapsed = max(0.001, time.time() - started)
    print(
        f"{label}: processed={processed} embedded={embedded} indexed={indexed} "
        f"failed={failed} elapsed_sec={elapsed:.1f}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

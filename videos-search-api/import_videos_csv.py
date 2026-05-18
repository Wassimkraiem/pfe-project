#!/usr/bin/env python3
"""Import videos from a CSV file into the API-backed DB."""

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urlparse


def resolve_default_api_key() -> str:
    if os.getenv("API_KEY"):
        return os.getenv("API_KEY", "")
    if os.getenv("API_KEYS"):
        return os.getenv("API_KEYS", "").split(",")[0].strip()
    env_path = Path(__file__).with_name(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key == "API_KEY" and value:
                return value
            if key == "API_KEYS" and value:
                return value.split(",")[0].strip()
    return "key1"


def normalize_base_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if not cleaned:
        return "http://localhost:5000"
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"
    cleaned = cleaned.replace("http://http://", "http://").replace(
        "https://https://", "https://"
    )
    parsed = urlparse(cleaned)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            f"Invalid --base-url value: {base_url!r}. Expected e.g. http://localhost:5000"
        )
    return cleaned

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import videos from CSV into /api/videos/ endpoint."
    )
    parser.add_argument(
        "--csv-path",
        default="videos.csv",
        help="Path to the CSV file (default: videos.csv).",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:5000",
        help="API base URL (default: http://localhost:5000).",
    )
    parser.add_argument(
        "--api-key",
        default=resolve_default_api_key(),
        help=(
            "API key sent as X-API-KEY header "
            "(default: API_KEY env, else first API_KEYS value, else .env value, else key1)."
        ),
    )
    parser.add_argument(
        "--service-identifier",
        default="rms",
        help="Service identifier for imported videos (default: rms).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of CSV rows to import.",
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=1,
        help="1-based CSV row index to start from (default: 1).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds (default: 20).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Sleep interval between requests in seconds (default: 0).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate rows without sending API requests.",
    )
    parser.add_argument(
        "--ensure-index",
        action="store_true",
        help="Bootstrap the vectorized videos_v2 index and read/write aliases before import.",
    )
    return parser.parse_args()


def parse_video_from_row(row: Dict[str, str]) -> Tuple[str, Dict]:
    """Return (video_id, video_data) from one CSV row."""
    has_single_video_info = set(row.keys()) == {"video_info"}
    if has_single_video_info:
        raw = row["video_info"]
        video_data = json.loads(raw)
    else:
        # New export format: parse `video_info` JSON when available and enrich with flat columns.
        base: Dict = {}
        raw_info = (row.get("video_info") or "").strip()
        if raw_info:
            try:
                parsed = json.loads(raw_info)
                if isinstance(parsed, dict):
                    base = parsed
            except json.JSONDecodeError:
                # Keep importing with flat columns even if nested JSON is malformed.
                base = {}

        flat: Dict = {}
        for k, v in row.items():
            if v is None:
                continue
            s = str(v).strip()
            if not s or k == "video_info":
                continue
            flat[k] = s

        # Prefer canto id as primary id, fallback to numeric id.
        if flat.get("canto_id"):
            base["id"] = flat["canto_id"]
        elif flat.get("id") and not base.get("id"):
            base["id"] = flat["id"]

        # Keep the flat source id for traceability.
        if flat.get("id"):
            base["source_id"] = flat["id"]

        # Normalize commonly queried fields.
        if flat.get("name") and not base.get("name"):
            base["name"] = flat["name"]
        if flat.get("name") and not base.get("title"):
            base["title"] = flat["name"]
        if flat.get("description"):
            base["description"] = flat["description"]
        if flat.get("category"):
            keyword = base.get("keyword")
            if isinstance(keyword, list):
                if flat["category"] not in keyword:
                    keyword.append(flat["category"])
            else:
                base["keyword"] = [flat["category"]]
        if flat.get("duration"):
            try:
                duration = float(flat["duration"])
                metadata = base.get("metadata")
                if not isinstance(metadata, dict):
                    metadata = {}
                    base["metadata"] = metadata
                metadata["duration"] = duration
            except ValueError:
                pass
        if flat.get("direct_url_original"):
            url = base.get("url")
            if not isinstance(url, dict):
                url = {}
                base["url"] = url
            url["directUrlOriginal"] = flat["direct_url_original"]
        if flat.get("direct_url_preview"):
            url = base.get("url")
            if not isinstance(url, dict):
                url = {}
                base["url"] = url
            url["directUrlPreview"] = flat["direct_url_preview"]

        # Persist original flat columns for debugging/filtering.
        base["cts"] = flat
        video_data = base

    video_id = video_data.get("id") or video_data.get("video_id") or row.get("canto_id")
    if not video_id:
        raise ValueError("Missing `id` or `video_id` in row payload")

    return str(video_id), video_data


def _coerce_minor_version(value):
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.isdigit():
            return int(s)
        parts = s.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            # Semver-like values (e.g. 0.2.0): keep the minor component.
            return int(parts[1])
    return None


def sanitize_video_data(video_data: Dict) -> Dict:
    metadata = video_data.get("metadata")
    if isinstance(metadata, dict) and "Minor_Version" in metadata:
        coerced = _coerce_minor_version(metadata.get("Minor_Version"))
        if coerced is None:
            metadata.pop("Minor_Version", None)
        else:
            metadata["Minor_Version"] = coerced
    if isinstance(metadata, dict) and "Android_Version" in metadata:
        android_version = metadata.get("Android_Version")
        if isinstance(android_version, int):
            pass
        elif isinstance(android_version, str):
            stripped = android_version.strip()
            if stripped.isdigit():
                metadata["Android_Version"] = int(stripped)
            else:
                parts = stripped.split(".")
                if parts and parts[0].isdigit():
                    metadata["Android_Version"] = int(parts[0])
                else:
                    metadata.pop("Android_Version", None)
        else:
            metadata.pop("Android_Version", None)
    ensure_views(video_data)
    return video_data


def ensure_views(video_data: Dict) -> None:
    # Keep existing valid views if present.
    existing = video_data.get("views")
    if isinstance(existing, (int, float)) and int(existing) > 0:
        video_data["views"] = int(existing)
        return
    if isinstance(existing, str):
        stripped = existing.strip().replace(",", "")
        if stripped.isdigit() and int(stripped) > 0:
            video_data["views"] = int(stripped)
            return

    # Deterministic pseudo-random assignment seeded by id/name so reruns are stable.
    seed_source = str(video_data.get("id") or video_data.get("video_id") or video_data.get("name") or "")
    digest = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()
    seed = int(digest[:16], 16)
    rng = random.Random(seed)

    # Weighted blend: some very high values in millions, others in thousands.
    if rng.random() < 0.4:
        views = rng.randint(1_000_000, 9_500_000)
    else:
        views = rng.randint(1_000, 950_000)
    video_data["views"] = views


def post_video(
    session,
    base_url: str,
    api_key: str,
    service_identifier: str,
    video_id: str,
    video_data: Dict,
    timeout: float,
):
    payload = {
        "video_id": video_id,
        "service_identifier": service_identifier,
        "video_data": video_data,
    }
    return session.post(
        f"{base_url.rstrip('/')}/api/videos/",
        json=payload,
        headers={"X-API-KEY": api_key},
        timeout=timeout,
    )


def ensure_videos_index(session, base_url: str, timeout: float) -> None:
    response = session.put(
        f"{base_url.rstrip('/')}/indexes/bootstrap-v2",
        json={
            "index_name": os.getenv("VIDEOS_INDEX_NAME", "videos_v2"),
            "read_alias": os.getenv("VIDEOS_READ_ALIAS", "videos_read"),
            "write_alias": os.getenv("VIDEOS_WRITE_ALIAS", "videos_write"),
            "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "1536")),
        },
        timeout=timeout,
    )
    if response.ok:
        print("Ensured vectorized OpenSearch video index and aliases exist.")
        return

    raise RuntimeError(
        f"Failed to bootstrap vectorized video index: status={response.status_code} body={response.text[:300]}"
    )


def main() -> int:
    args = parse_args()
    try:
        args.base_url = normalize_base_url(args.base_url)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    csv_path = args.csv_path

    if args.start_row < 1:
        print("ERROR: --start-row must be >= 1", file=sys.stderr)
        return 2

    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        return 2

    total = 0
    imported = 0
    failed = 0
    skipped = 0

    session = None
    if not args.dry_run:
        try:
            import requests  # type: ignore
        except ModuleNotFoundError:
            print(
                "ERROR: `requests` is required for non-dry-run imports. "
                "Install it with: pip install requests",
                file=sys.stderr,
            )
            return 2
        session = requests.Session()
        if args.ensure_index:
            ensure_videos_index(session, args.base_url, args.timeout)
    started_at = time.time()

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader, start=1):
            if idx < args.start_row:
                skipped += 1
                continue

            if args.limit is not None and total >= args.limit:
                break

            total += 1

            try:
                video_id, video_data = parse_video_from_row(row)
                video_data = sanitize_video_data(video_data)
                if args.dry_run:
                    imported += 1
                    if imported % 100 == 0:
                        print(f"[dry-run] validated {imported} rows...")
                    continue

                response = post_video(
                    session=session,
                    base_url=args.base_url,
                    api_key=args.api_key,
                    service_identifier=args.service_identifier,
                    video_id=video_id,
                    video_data=video_data,
                    timeout=args.timeout,
                )

                if response.ok:
                    imported += 1
                    if imported % 100 == 0:
                        print(f"Imported {imported} rows...")
                else:
                    failed += 1
                    print(
                        f"[row={idx}] FAIL video_id={video_id} "
                        f"status={response.status_code} body={response.text[:300]}",
                        file=sys.stderr,
                    )
            except Exception as exc:
                failed += 1
                print(f"[row={idx}] FAIL parse/upload error: {exc}", file=sys.stderr)

            if args.sleep > 0:
                time.sleep(args.sleep)

    elapsed = time.time() - started_at
    print("\nImport summary")
    print(f"- csv_path: {csv_path}")
    print(f"- processed: {total}")
    print(f"- imported: {imported}")
    print(f"- failed: {failed}")
    print(f"- skipped_before_start_row: {skipped}")
    print(f"- elapsed_sec: {elapsed:.2f}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

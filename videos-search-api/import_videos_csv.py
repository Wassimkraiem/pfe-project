#!/usr/bin/env python3
"""Import videos from a CSV file into the API-backed DB."""

import argparse
import csv
import json
import os
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
        help="Create OpenSearch index `videos` via /indexes/ before import.",
    )
    return parser.parse_args()


def parse_video_from_row(row: Dict[str, str]) -> Tuple[str, Dict]:
    """Return (video_id, video_data) from one CSV row."""
    if "video_info" in row:
        raw = row["video_info"]
        video_data = json.loads(raw)
    else:
        video_data = row

    video_id = video_data.get("id") or video_data.get("video_id")
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
    return video_data


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
        f"{base_url.rstrip('/')}/indexes/",
        json={"index_name": "videos"},
        timeout=timeout,
    )
    if response.ok:
        print("Ensured OpenSearch index `videos` exists.")
        return

    # Existing index is not fatal for import.
    if "index already exists" in response.text.lower():
        print("OpenSearch index `videos` already exists.")
        return

    raise RuntimeError(
        f"Failed to create index `videos`: status={response.status_code} body={response.text[:300]}"
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

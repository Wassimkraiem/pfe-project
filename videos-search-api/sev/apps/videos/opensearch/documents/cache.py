"""Redis-backed cache helpers for the videos search API.

All operations are fail-open: any connection/serialization error is swallowed
and logged so that callers transparently fall through to the underlying
OpenSearch pipeline.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover - redis is a runtime dep
    redis = None  # type: ignore[assignment]


_client: "redis.Redis | None" = None
_client_init_error: Exception | None = None


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    return _env_flag("SEARCH_CACHE_ENABLED", default=True)


def _get_client() -> "redis.Redis | None":
    global _client, _client_init_error

    if not is_enabled():
        return None
    if _client is not None:
        return _client
    if _client_init_error is not None:
        return None
    if redis is None:
        _client_init_error = RuntimeError("redis package not installed")
        return None

    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
        client.ping()
        _client = client
        return _client
    except Exception as exc:
        _client_init_error = exc
        print(f"[search-cache] Redis unavailable ({url}): {exc}")
        return None


def make_key(prefix: str, payload: Any) -> str:
    """Build a stable cache key from a JSON-serializable payload."""
    serialized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha1(serialized.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def cache_get(key: str) -> Any | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        print(f"[search-cache] GET {key} failed: {exc}")
        return None


def cache_set(key: str, value: Any, ttl: int) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        payload = json.dumps(value, default=str, separators=(",", ":"))
        client.setex(key, max(1, int(ttl)), payload)
    except Exception as exc:
        print(f"[search-cache] SET {key} failed: {exc}")


def get_ttl() -> int:
    raw = os.environ.get("SEARCH_CACHE_TTL")
    if raw is None:
        return 300
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 300

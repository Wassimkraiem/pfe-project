from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Protocol


logger = logging.getLogger(__name__)

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore[assignment]


@dataclass(slots=True)
class HistoryMessage:
    role: str
    content: str


class ChatHistoryStore(Protocol):
    async def get_history_text(self, user_id: str) -> str: ...

    async def append_turn(self, user_id: str, user_message: str, assistant_message: str) -> None: ...

    async def get_state(self, user_id: str, key: str) -> dict[str, Any] | None: ...

    async def set_state(self, user_id: str, key: str, value: dict[str, Any]) -> None: ...


class InMemoryChatHistoryStore:
    def __init__(self, max_messages: int) -> None:
        self._max_messages = max_messages
        self._messages: dict[str, deque[HistoryMessage]] = defaultdict(
            lambda: deque(maxlen=self._max_messages)
        )
        self._state: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    async def get_history_text(self, user_id: str) -> str:
        async with self._lock:
            messages = list(self._messages.get(user_id, ()))
        return "\n".join(f"{message.role}: {message.content}" for message in messages)

    async def append_turn(self, user_id: str, user_message: str, assistant_message: str) -> None:
        async with self._lock:
            history = self._messages[user_id]
            history.append(HistoryMessage(role="user", content=user_message))
            history.append(HistoryMessage(role="assistant", content=assistant_message))

    async def get_state(self, user_id: str, key: str) -> dict[str, Any] | None:
        async with self._lock:
            value = self._state.get(user_id, {}).get(key)
        return dict(value) if isinstance(value, dict) else None

    async def set_state(self, user_id: str, key: str, value: dict[str, Any]) -> None:
        async with self._lock:
            self._state[user_id][key] = dict(value)


class RedisChatHistoryStore:
    def __init__(self, redis: Any, *, max_messages: int, ttl_seconds: int) -> None:
        self._redis = redis
        self._max_messages = max_messages
        self._ttl_seconds = ttl_seconds

    @classmethod
    async def create(cls, redis_url: str, *, max_messages: int, ttl_seconds: int) -> "RedisChatHistoryStore":
        if Redis is None:
            raise RuntimeError("redis package is not installed")
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        return cls(redis, max_messages=max_messages, ttl_seconds=ttl_seconds)

    async def close(self) -> None:
        await self._redis.aclose()

    def _history_key(self, user_id: str) -> str:
        return f"chat_history:{user_id}:messages"

    def _state_key(self, user_id: str, key: str) -> str:
        return f"chat_history:{user_id}:state:{key}"

    async def get_history_text(self, user_id: str) -> str:
        rows = await self._redis.lrange(self._history_key(user_id), 0, self._max_messages - 1)
        messages: list[HistoryMessage] = []
        for row in rows:
            try:
                parsed = json.loads(row)
            except json.JSONDecodeError:
                continue
            role = parsed.get("role")
            content = parsed.get("content")
            if isinstance(role, str) and isinstance(content, str):
                messages.append(HistoryMessage(role=role, content=content))
        return "\n".join(f"{message.role}: {message.content}" for message in messages)

    async def append_turn(self, user_id: str, user_message: str, assistant_message: str) -> None:
        key = self._history_key(user_id)
        values = [
            json.dumps({"role": "user", "content": user_message}, ensure_ascii=False),
            json.dumps({"role": "assistant", "content": assistant_message}, ensure_ascii=False),
        ]
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.rpush(key, *values)
            pipe.ltrim(key, -self._max_messages, -1)
            pipe.expire(key, self._ttl_seconds)
            await pipe.execute()

    async def get_state(self, user_id: str, key: str) -> dict[str, Any] | None:
        raw = await self._redis.get(self._state_key(user_id, key))
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    async def set_state(self, user_id: str, key: str, value: dict[str, Any]) -> None:
        redis_key = self._state_key(user_id, key)
        await self._redis.set(redis_key, json.dumps(value, ensure_ascii=False), ex=self._ttl_seconds)


async def build_chat_history_store(
    *,
    max_messages: int,
    redis_url: str,
    ttl_seconds: int,
) -> ChatHistoryStore:
    if redis_url.strip():
        try:
            return await RedisChatHistoryStore.create(
                redis_url.strip(),
                max_messages=max_messages,
                ttl_seconds=ttl_seconds,
            )
        except Exception:
            logger.exception("Redis chat history is unavailable; falling back to in-memory history")
    return InMemoryChatHistoryStore(max_messages=max_messages)

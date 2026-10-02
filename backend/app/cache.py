"""Redis-backed query-result cache and agent session store."""

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis


class QueryCache:
    def __init__(self, redis: Redis, ttl_seconds: int, prefix: str = "testlens:query:") -> None:
        self._redis = redis
        self._ttl = ttl_seconds
        self._prefix = prefix

    def key(self, name: str, arguments: dict[str, Any]) -> str:
        digest = hashlib.sha256(
            json.dumps(arguments, sort_keys=True, default=str).encode()
        ).hexdigest()[:32]
        return f"{self._prefix}{name}:{digest}"

    async def get_or_compute(
        self,
        name: str,
        arguments: dict[str, Any],
        compute: Callable[[], Awaitable[list[dict[str, Any]]]],
    ) -> tuple[list[dict[str, Any]], bool]:
        """Return (rows, cache_hit)."""
        key = self.key(name, arguments)
        cached = await self._redis.get(key)
        if cached is not None:
            return json.loads(cached), True
        rows = await compute()
        await self._redis.set(key, json.dumps(rows, default=str), ex=self._ttl)
        return rows, False


class SessionStore:
    """Persists each session's provider-native transcript as JSON."""

    def __init__(self, redis: Redis, ttl_seconds: int, prefix: str = "testlens:session:") -> None:
        self._redis = redis
        self._ttl = ttl_seconds
        self._prefix = prefix

    async def load(self, session_id: str) -> list[dict[str, Any]]:
        raw = await self._redis.get(self._prefix + session_id)
        return json.loads(raw) if raw else []

    async def save(self, session_id: str, transcript: list[dict[str, Any]]) -> None:
        await self._redis.set(self._prefix + session_id, json.dumps(transcript), ex=self._ttl)

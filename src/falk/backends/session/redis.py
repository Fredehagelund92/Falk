"""Redis-backed session store backend."""

from __future__ import annotations

import json
from typing import Any


class RedisSessionStore:
    """Redis-backed session store.

    Suitable for multi-worker deployments with shared state.
    """

    def __init__(self, url: str = "redis://localhost:6379", ttl: int = 3600):
        try:
            import redis
        except ImportError as err:
            raise ImportError(
                "Redis session store requires redis package. Install with: uv add redis"
            ) from err
        self._client = redis.from_url(url, decode_responses=True)
        self._ttl = ttl

    def get(self, session_id: str) -> dict[str, Any] | None:
        data = self._client.get(f"falk:session:{session_id}")
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    def set(self, session_id: str, state: dict[str, Any]) -> None:
        key = f"falk:session:{session_id}"
        self._client.setex(key, self._ttl, json.dumps(state))

    def clear(self, session_id: str) -> None:
        self._client.delete(f"falk:session:{session_id}")

"""In-memory session store backend."""

from __future__ import annotations

from typing import Any

from cachetools import TTLCache


class MemorySessionStore:
    """In-memory session store using cachetools TTLCache.

    Suitable for single-process deployments or development.
    """

    def __init__(self, maxsize: int = 500, ttl: int = 3600):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, session_id: str) -> dict[str, Any] | None:
        return self._cache.get(session_id)

    def set(self, session_id: str, state: dict[str, Any]) -> None:
        self._cache[session_id] = state

    def clear(self, session_id: str) -> None:
        self._cache.pop(session_id, None)

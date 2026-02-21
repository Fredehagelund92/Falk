"""Session state storage for multi-user support.

Provides pluggable storage backends (memory, Redis) for session state.

Usage:
    # Memory store (default, single process)
    session:
      store: memory
      maxsize: 500
      ttl: 3600
    
    # Redis store (multi-worker)
    session:
      store: redis
      url: redis://localhost:6379
      ttl: 3600
    
    # Or via environment variables
    SESSION_STORE=redis
    SESSION_URL=redis://localhost:6379
    SESSION_TTL=3600

Install Redis support:
    uv add redis
    # or: uv sync --extra redis
"""
from __future__ import annotations

import json
import os
from typing import Any, Protocol

from cachetools import TTLCache


class SessionStore(Protocol):
    """Interface for session state storage."""

    def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session state by ID. Returns None if not found."""
        ...

    def set(self, session_id: str, state: dict[str, Any]) -> None:
        """Set session state."""
        ...

    def clear(self, session_id: str) -> None:
        """Clear session state."""
        ...


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


class RedisSessionStore:
    """Redis-backed session store.
    
    Suitable for multi-worker deployments with shared state.
    """

    def __init__(self, url: str = "redis://localhost:6379", ttl: int = 3600):
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis session store requires redis package. Install with: uv add redis"
            )
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


def _load_session_config() -> Any | None:
    """Best-effort settings loader for session config."""
    try:
        from falk.settings import load_settings
        settings = load_settings()
        return settings.session if hasattr(settings, "session") else None
    except Exception:
        return None


def _int_with_default(value: str | None, default: int) -> int:
    """Parse int env values safely with fallback."""
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def create_session_store() -> SessionStore:
    """Factory to create session store based on config.
    
    Precedence for all fields: env vars > falk_project.yaml > defaults.
    """
    session_cfg = _load_session_config()
    store_type = (
        (os.getenv("SESSION_STORE") or (getattr(session_cfg, "store", None) if session_cfg else None) or "memory")
        .strip()
        .lower()
    )
    ttl = _int_with_default(
        os.getenv("SESSION_TTL"),
        getattr(session_cfg, "ttl", 3600) if session_cfg else 3600,
    )

    if store_type == "redis":
        url = (
            os.getenv("SESSION_URL")
            or os.getenv("REDIS_URL")
            or (getattr(session_cfg, "url", None) if session_cfg else None)
            or "redis://localhost:6379"
        )
        return RedisSessionStore(url=url, ttl=ttl)

    maxsize = _int_with_default(
        os.getenv("SESSION_MAXSIZE"),
        getattr(session_cfg, "maxsize", 500) if session_cfg else 500,
    )
    return MemorySessionStore(maxsize=maxsize, ttl=ttl)

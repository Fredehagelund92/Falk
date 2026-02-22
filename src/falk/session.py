"""Session state storage for multi-user support.

Provides pluggable storage backends (postgres, memory) for session state.

Usage:
    # Postgres store (default, production)
    session:
      store: postgres
      postgres_url: ${POSTGRES_URL}
      schema: falk_session
      ttl: 3600

    # Memory store (dev fallback, single process)
    session:
      store: memory
      maxsize: 500
      ttl: 3600

    # Or via environment variables
    SESSION_STORE=postgres
    POSTGRES_URL=postgresql://user:pass@host:5432/db
    SESSION_TTL=3600
"""
from __future__ import annotations

import os
from typing import Any, Protocol

from falk.backends.session import MemorySessionStore, PostgresSessionStore


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
        (os.getenv("SESSION_STORE") or (getattr(session_cfg, "store", None) if session_cfg else None) or "postgres")
        .strip()
        .lower()
    )
    ttl = _int_with_default(
        os.getenv("SESSION_TTL"),
        getattr(session_cfg, "ttl", 3600) if session_cfg else 3600,
    )

    if store_type == "postgres":
        postgres_url = (
            os.getenv("POSTGRES_URL")
            or (getattr(session_cfg, "postgres_url", None) if session_cfg else None)
            or ""
        )
        if not postgres_url or not postgres_url.strip():
            import logging
            logging.getLogger(__name__).warning(
                "session.store=postgres but POSTGRES_URL not set; falling back to memory. "
                "Set POSTGRES_URL in .env for production."
            )
        else:
            schema = (
                os.getenv("SESSION_SCHEMA")
                or (getattr(session_cfg, "schema", None) if session_cfg else None)
                or "falk_session"
            )
            return PostgresSessionStore(url=postgres_url, schema=schema, ttl=ttl)

    maxsize = _int_with_default(
        os.getenv("SESSION_MAXSIZE"),
        getattr(session_cfg, "maxsize", 500) if session_cfg else 500,
    )
    return MemorySessionStore(maxsize=maxsize, ttl=ttl)

"""Session/context helpers for LLM tools."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext

from falk.agent import DataAgent
from falk.session import SessionStore, create_session_store

if TYPE_CHECKING:
    from falk.settings import AccessConfig


_session_store: SessionStore | None = None
_session_aggregates: dict[str, Any] = {}


def get_session_store() -> SessionStore:
    """Lazily initialize session store to avoid import-time coupling."""
    global _session_store
    if _session_store is None:
        _session_store = create_session_store()
    return _session_store


def session_id(ctx: RunContext[DataAgent]) -> str:
    """Compute session ID from context metadata."""
    if not ctx.metadata:
        return "default"
    thread_ts = ctx.metadata.get("thread_ts")
    if thread_ts:
        return str(thread_ts)
    channel = ctx.metadata.get("channel")
    user_id = ctx.metadata.get("user_id")
    if channel and user_id:
        return f"{channel}:{user_id}"
    if user_id:
        return str(user_id)
    return "default"


def get_session_state(ctx: RunContext[DataAgent]) -> dict[str, Any]:
    """Get or create session state for the current context."""
    sid = session_id(ctx)
    store = get_session_store()
    state = store.get(sid)
    if not state:
        clear_session_aggregate(sid)
        state = {
            "last_query_data": [],
            "last_query_metric": None,
            "pending_files": [],
        }
        store.set(sid, state)
    return state


def user_id(ctx: RunContext[DataAgent]) -> str | None:
    """Safely extract user_id from context metadata."""
    return ctx.metadata.get("user_id") if ctx.metadata else None


def access_cfg(ctx: RunContext[DataAgent]) -> "AccessConfig":
    """Return the AccessConfig from the agent settings."""
    return ctx.deps._settings.access


def get_pending_files_for_session(session_id_value: str) -> list[dict[str, Any]]:
    """Get pending files for a specific session (for Slack upload)."""
    state = get_session_store().get(session_id_value)
    if state:
        return state.get("pending_files", [])
    clear_session_aggregate(session_id_value)
    return []


def clear_pending_files_for_session(session_id_value: str) -> None:
    """Clear pending files for a specific session (after Slack upload)."""
    store = get_session_store()
    state = store.get(session_id_value)
    if state:
        state["pending_files"] = []
        store.set(session_id_value, state)
    clear_session_aggregate(session_id_value)


def get_session_aggregate(session_id_value: str) -> Any | None:
    """Read ephemeral aggregate object for chart generation."""
    return _session_aggregates.get(session_id_value)


def set_session_aggregate(session_id_value: str, aggregate: Any | None) -> None:
    """Store ephemeral aggregate object for chart generation."""
    if aggregate is None:
        _session_aggregates.pop(session_id_value, None)
        return
    _session_aggregates[session_id_value] = aggregate


def clear_session_aggregate(session_id_value: str) -> None:
    """Remove ephemeral aggregate object for a session."""
    _session_aggregates.pop(session_id_value, None)

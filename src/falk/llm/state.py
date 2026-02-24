"""Session/context helpers for LLM tools.

Runtime state is stored in SessionStore (postgres or memory). All session-critical
data lives in the store for multi-worker correctness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext

from falk.agent import DataAgent
from falk.session import SessionStore, create_session_store

if TYPE_CHECKING:
    from falk.settings import AccessConfig


@dataclass
class RuntimeState:
    """Typed runtime state for a session. JSON-safe for session storage."""

    last_query_data: list[dict[str, Any]] = field(default_factory=list)
    last_query_metric: list[str] | str | None = None
    last_query_params: dict[str, Any] | None = (
        None  # For chart re-run: metrics, group_by, filters, order, limit, time_grain
    )
    pending_files: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for SessionStore (JSON-safe)."""
        return {
            "last_query_data": self.last_query_data,
            "last_query_metric": self.last_query_metric,
            "last_query_params": self.last_query_params,
            "pending_files": self.pending_files,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RuntimeState:
        """Deserialize from SessionStore."""
        if not data:
            return cls()
        return cls(
            last_query_data=data.get("last_query_data") or [],
            last_query_metric=data.get("last_query_metric"),
            last_query_params=data.get("last_query_params"),
            pending_files=data.get("pending_files") or [],
        )


_session_store: SessionStore | None = None


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


def get_runtime_state(ctx: RunContext[DataAgent]) -> RuntimeState:
    """Get or create runtime state for the current context."""
    sid = session_id(ctx)
    store = get_session_store()
    raw = store.get(sid)
    return RuntimeState.from_dict(raw)


def save_runtime_state(ctx: RunContext[DataAgent], state: RuntimeState) -> None:
    """Persist runtime state for the current context."""
    sid = session_id(ctx)
    get_session_store().set(sid, state.to_dict())


def get_session_state(ctx: RunContext[DataAgent]) -> RuntimeState:
    """Alias for get_runtime_state for backward compatibility."""
    return get_runtime_state(ctx)


def user_id(ctx: RunContext[DataAgent]) -> str | None:
    """Safely extract user_id from context metadata."""
    return ctx.metadata.get("user_id") if ctx.metadata else None


def access_cfg(ctx: RunContext[DataAgent]) -> AccessConfig:
    """Return the AccessConfig from the agent settings."""
    return ctx.deps._settings.access


def get_pending_files_for_session(session_id_value: str) -> list[dict[str, Any]]:
    """Get pending files for a specific session (for Slack upload)."""
    raw = get_session_store().get(session_id_value)
    state = RuntimeState.from_dict(raw)
    return state.pending_files


def clear_pending_files_for_session(session_id_value: str) -> None:
    """Clear pending files for a specific session (after Slack upload)."""
    store = get_session_store()
    raw = store.get(session_id_value)
    if raw is not None:
        state = RuntimeState.from_dict(raw)
        state.pending_files = []
        store.set(session_id_value, state.to_dict())

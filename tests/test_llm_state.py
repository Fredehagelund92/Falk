from __future__ import annotations

from falk.llm.state import (
    RuntimeState,
    clear_pending_files_for_session,
    get_pending_files_for_session,
)
from falk.llm import state as state_mod
from falk.session import MemorySessionStore


class _DummyCtx:
    def __init__(self, metadata):
        self.metadata = metadata


def test_get_runtime_state_has_typed_schema(monkeypatch):
    monkeypatch.setattr(state_mod, "_session_store", MemorySessionStore(maxsize=10, ttl=60))

    state = state_mod.get_runtime_state(_DummyCtx({"thread_ts": "t-1"}))

    assert isinstance(state, RuntimeState)
    assert state.last_query_data == []
    assert state.last_query_metric is None
    assert state.last_query_params is None
    assert state.pending_files == []


def test_runtime_state_serialization():
    state = RuntimeState(
        last_query_data=[{"a": 1}],
        last_query_metric=["m"],
        last_query_params={"metrics": ["m"], "group_by": ["d"]},
        pending_files=[{"path": "x.csv", "title": "x.csv"}],
    )
    d = state.to_dict()
    restored = RuntimeState.from_dict(d)
    assert restored.last_query_data == state.last_query_data
    assert restored.last_query_metric == state.last_query_metric
    assert restored.last_query_params == state.last_query_params
    assert restored.pending_files == state.pending_files


def test_clear_pending_files_updates_store(monkeypatch):
    store = MemorySessionStore(maxsize=10, ttl=60)
    sid = "session-2"
    store.set(
        sid,
        {
            "last_query_data": [{"a": 1}],
            "last_query_metric": ["m"],
            "last_query_params": {"metrics": ["m"]},
            "pending_files": [{"path": "x.csv", "title": "x.csv"}],
        },
    )

    monkeypatch.setattr(state_mod, "_session_store", store)

    clear_pending_files_for_session(sid)
    persisted = store.get(sid)

    assert persisted is not None
    assert persisted["pending_files"] == []


def test_get_pending_files_returns_empty_when_no_session(monkeypatch):
    sid = "session-3"
    monkeypatch.setattr(state_mod, "_session_store", MemorySessionStore(maxsize=10, ttl=60))

    files = get_pending_files_for_session(sid)

    assert files == []


def test_state_mutating_tools_are_sequential():
    """State-mutating tools must run sequentially to avoid race conditions."""
    from falk.llm.tools import data_tools

    mutating_tools = {"query_metric", "export", "generate_chart"}
    for name, tool in data_tools.tools.items():
        if name in mutating_tools:
            assert tool.sequential, f"Tool {name} mutates session state and must be sequential"

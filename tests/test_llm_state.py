from __future__ import annotations

from falk.llm import state as state_mod
from falk.session import MemorySessionStore


class _DummyCtx:
    def __init__(self, metadata):
        self.metadata = metadata


def test_get_session_state_has_json_safe_schema(monkeypatch):
    monkeypatch.setattr(state_mod, "_session_store", MemorySessionStore(maxsize=10, ttl=60))
    monkeypatch.setattr(state_mod, "_session_aggregates", {})

    state = state_mod.get_session_state(_DummyCtx({"thread_ts": "t-1"}))

    assert set(state.keys()) == {"last_query_data", "last_query_metric", "pending_files"}


def test_session_aggregate_cache_lifecycle(monkeypatch):
    monkeypatch.setattr(state_mod, "_session_aggregates", {})

    sid = "session-1"
    aggregate = object()
    state_mod.set_session_aggregate(sid, aggregate)
    assert state_mod.get_session_aggregate(sid) is aggregate

    state_mod.clear_session_aggregate(sid)
    assert state_mod.get_session_aggregate(sid) is None


def test_clear_pending_files_also_clears_ephemeral_aggregate(monkeypatch):
    store = MemorySessionStore(maxsize=10, ttl=60)
    sid = "session-2"
    store.set(
        sid,
        {
            "last_query_data": [{"a": 1}],
            "last_query_metric": ["m"],
            "pending_files": [{"path": "x.csv", "title": "x.csv"}],
        },
    )

    monkeypatch.setattr(state_mod, "_session_store", store)
    monkeypatch.setattr(state_mod, "_session_aggregates", {sid: object()})

    state_mod.clear_pending_files_for_session(sid)
    persisted = store.get(sid)

    assert persisted is not None
    assert persisted["pending_files"] == []
    assert state_mod.get_session_aggregate(sid) is None


def test_missing_persisted_state_clears_stale_aggregate(monkeypatch):
    sid = "session-3"
    monkeypatch.setattr(state_mod, "_session_store", MemorySessionStore(maxsize=10, ttl=60))
    monkeypatch.setattr(state_mod, "_session_aggregates", {sid: object()})

    files = state_mod.get_pending_files_for_session(sid)

    assert files == []
    assert state_mod.get_session_aggregate(sid) is None

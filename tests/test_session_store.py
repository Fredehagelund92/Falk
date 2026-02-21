from __future__ import annotations

import json
from types import SimpleNamespace

from falk import session as session_mod


def test_create_session_store_uses_yaml_defaults_for_memory(monkeypatch):
    monkeypatch.delenv("SESSION_STORE", raising=False)
    monkeypatch.delenv("SESSION_TTL", raising=False)
    monkeypatch.delenv("SESSION_MAXSIZE", raising=False)
    monkeypatch.setattr(
        session_mod,
        "_load_session_config",
        lambda: SimpleNamespace(store="memory", ttl=111, maxsize=222, url="redis://yaml"),
    )

    store = session_mod.create_session_store()

    assert isinstance(store, session_mod.MemorySessionStore)
    assert store._cache.maxsize == 222
    assert store._cache.ttl == 111


def test_create_session_store_env_overrides_yaml_for_memory(monkeypatch):
    monkeypatch.setenv("SESSION_STORE", "memory")
    monkeypatch.setenv("SESSION_TTL", "333")
    monkeypatch.setenv("SESSION_MAXSIZE", "444")
    monkeypatch.setattr(
        session_mod,
        "_load_session_config",
        lambda: SimpleNamespace(store="memory", ttl=111, maxsize=222, url="redis://yaml"),
    )

    store = session_mod.create_session_store()

    assert isinstance(store, session_mod.MemorySessionStore)
    assert store._cache.maxsize == 444
    assert store._cache.ttl == 333


def test_create_session_store_uses_env_url_precedence_for_redis(monkeypatch):
    class FakeRedisStore:
        def __init__(self, url: str, ttl: int):
            self.url = url
            self.ttl = ttl

    monkeypatch.setenv("SESSION_STORE", "redis")
    monkeypatch.setenv("SESSION_URL", "redis://session-url")
    monkeypatch.setenv("REDIS_URL", "redis://redis-url")
    monkeypatch.setenv("SESSION_TTL", "42")
    monkeypatch.setattr(
        session_mod,
        "_load_session_config",
        lambda: SimpleNamespace(store="redis", ttl=111, maxsize=222, url="redis://yaml"),
    )
    monkeypatch.setattr(session_mod, "RedisSessionStore", FakeRedisStore)

    store = session_mod.create_session_store()

    assert isinstance(store, FakeRedisStore)
    assert store.url == "redis://session-url"
    assert store.ttl == 42


def test_redis_store_set_serializes_json_safe_payload():
    class FakeClient:
        def __init__(self):
            self.last = None

        def setex(self, key, ttl, payload):
            self.last = (key, ttl, payload)

    fake_client = FakeClient()
    store = session_mod.RedisSessionStore.__new__(session_mod.RedisSessionStore)
    store._client = fake_client
    store._ttl = 300

    state = {
        "last_query_data": [{"metric": 10}],
        "last_query_metric": ["revenue"],
        "pending_files": [],
    }
    store.set("s1", state)

    key, ttl, payload = fake_client.last
    assert key == "falk:session:s1"
    assert ttl == 300
    assert json.loads(payload) == state

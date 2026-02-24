from __future__ import annotations

from types import SimpleNamespace

from falk import session as session_mod


def test_create_session_store_defaults_to_memory_when_not_configured(monkeypatch):
    """Default to memory when no session config (works out of the box)."""
    monkeypatch.delenv("SESSION_STORE", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.setattr(session_mod, "_load_session_config", lambda: None)

    store = session_mod.create_session_store()

    assert isinstance(store, session_mod.MemorySessionStore)


def test_create_session_store_uses_yaml_defaults_for_memory(monkeypatch):
    monkeypatch.delenv("SESSION_STORE", raising=False)
    monkeypatch.delenv("SESSION_TTL", raising=False)
    monkeypatch.delenv("SESSION_MAXSIZE", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.setattr(
        session_mod,
        "_load_session_config",
        lambda: SimpleNamespace(
            store="memory", ttl=111, maxsize=222, postgres_url="", schema="falk_session"
        ),
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
        lambda: SimpleNamespace(
            store="memory", ttl=111, maxsize=222, postgres_url="", schema="falk_session"
        ),
    )

    store = session_mod.create_session_store()

    assert isinstance(store, session_mod.MemorySessionStore)
    assert store._cache.maxsize == 444
    assert store._cache.ttl == 333


def test_create_session_store_uses_env_url_precedence_for_postgres(monkeypatch):
    class FakePostgresStore:
        def __init__(self, url: str, schema: str, ttl: int):
            self.url = url
            self.schema = schema
            self.ttl = ttl

    monkeypatch.setenv("SESSION_STORE", "postgres")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pass@localhost:5432/falk")
    monkeypatch.setenv("SESSION_SCHEMA", "custom_schema")
    monkeypatch.setenv("SESSION_TTL", "42")
    monkeypatch.setattr(
        session_mod,
        "_load_session_config",
        lambda: SimpleNamespace(
            store="postgres",
            ttl=111,
            maxsize=222,
            postgres_url="postgresql://yaml",
            schema="falk_session",
        ),
    )
    monkeypatch.setattr(session_mod, "PostgresSessionStore", FakePostgresStore)

    store = session_mod.create_session_store()

    assert isinstance(store, FakePostgresStore)
    assert store.url == "postgresql://user:pass@localhost:5432/falk"
    assert store.schema == "custom_schema"
    assert store.ttl == 42


def test_create_session_store_raises_when_postgres_url_empty(monkeypatch):
    """Fail fast when postgres is configured but POSTGRES_URL is missing."""
    monkeypatch.setenv("SESSION_STORE", "postgres")
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.setattr(
        session_mod,
        "_load_session_config",
        lambda: SimpleNamespace(
            store="postgres", ttl=3600, maxsize=500, postgres_url="", schema="falk_session"
        ),
    )

    import pytest

    with pytest.raises(ValueError, match="POSTGRES_URL"):
        session_mod.create_session_store()


def test_create_session_store_raises_when_postgres_url_unresolved(monkeypatch):
    """Fail fast when postgres_url is literal ${POSTGRES_URL} and env unset."""
    monkeypatch.setenv("SESSION_STORE", "postgres")
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.setattr(
        session_mod,
        "_load_session_config",
        lambda: SimpleNamespace(
            store="postgres",
            ttl=3600,
            maxsize=500,
            postgres_url="${POSTGRES_URL}",
            schema="falk_session",
        ),
    )

    import pytest

    with pytest.raises(ValueError, match="POSTGRES_URL"):
        session_mod.create_session_store()


def test_postgres_store_raises_when_url_empty():
    import pytest

    from falk.backends.session.postgres import PostgresSessionStore

    with pytest.raises(ValueError, match="POSTGRES_URL"):
        PostgresSessionStore(url="", schema="falk_session", ttl=3600)


def test_memory_store_set_get_roundtrip():
    store = session_mod.MemorySessionStore(maxsize=100, ttl=3600)
    state = {
        "last_query_data": [{"metric": 10}],
        "last_query_metric": ["revenue"],
        "pending_files": [],
    }
    store.set("s1", state)
    assert store.get("s1") == state
    store.clear("s1")
    assert store.get("s1") is None

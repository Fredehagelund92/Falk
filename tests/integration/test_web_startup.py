from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.applications import Starlette

from falk import build_web_app


class _FakeAgent:
    def to_web(self, deps=None):
        return FastAPI()


class _StarletteAgent:
    """Agent that returns Starlette (not FastAPI) to exercise mount path."""

    def to_web(self, deps=None):
        return Starlette()


class _HealthyConnection:
    def list_tables(self):
        return []


class _FakeCore:
    def __init__(self):
        self.bsl_models = {"orders": object()}
        self.ibis_connection = _HealthyConnection()


def test_build_web_app_initializes_core_when_not_provided(monkeypatch):
    monkeypatch.setattr("falk.llm.builder.build_agent", lambda: _FakeAgent())
    monkeypatch.setattr("falk.llm.builder.DataAgent", _FakeCore)

    app = build_web_app()

    assert app is not None


def test_build_web_app_bubbles_core_init_failure(monkeypatch):
    monkeypatch.setattr("falk.llm.builder.build_agent", lambda: _FakeAgent())

    class _BrokenCore:
        def __init__(self):
            raise RuntimeError("cannot connect")

    monkeypatch.setattr("falk.llm.builder.DataAgent", _BrokenCore)

    with pytest.raises(RuntimeError, match="cannot connect"):
        build_web_app()


def test_build_web_app_works_when_to_web_returns_starlette(monkeypatch):
    """Regression: build_web_app must not use include_router on agent app.

    When to_web() returns Starlette (not FastAPI), include_router would fail.
    We mount the agent app instead, so the host FastAPI app always works.
    """
    monkeypatch.setattr("falk.llm.builder.build_agent", lambda: _StarletteAgent())
    monkeypatch.setattr("falk.llm.builder.DataAgent", _FakeCore)

    app = build_web_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from falk.llm import build_web_app


class _FakeAgent:
    def to_web(self, deps=None):
        return FastAPI()


class _HealthyConnection:
    def list_tables(self):
        return ["orders"]


class _HealthyCore:
    bsl_models = {"orders": object()}
    ibis_connection = _HealthyConnection()


class _FailingConnection:
    def list_tables(self):
        raise RuntimeError("warehouse unavailable")


class _DegradedCore:
    bsl_models = {}
    ibis_connection = _FailingConnection()


def test_web_health_endpoint_returns_ok(monkeypatch):
    monkeypatch.setattr("falk.llm.builder.build_agent", lambda: _FakeAgent())
    app = build_web_app(core=_HealthyCore())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_web_ready_returns_ready_when_checks_pass(monkeypatch):
    monkeypatch.setattr("falk.llm.builder.build_agent", lambda: _FakeAgent())
    app = build_web_app(core=_HealthyCore())
    client = TestClient(app)

    response = client.get("/ready")
    payload = response.json()

    assert response.status_code == 200
    assert payload["ready"] is True
    assert payload["data_agent_initialized"] is True
    assert payload["semantic_models_loaded"] is True
    assert payload["warehouse_connection_ok"] is True


def test_web_ready_returns_503_when_checks_fail(monkeypatch):
    monkeypatch.setattr("falk.llm.builder.build_agent", lambda: _FakeAgent())
    app = build_web_app(core=_DegradedCore())
    client = TestClient(app)

    response = client.get("/ready")
    payload = response.json()

    assert response.status_code == 503
    assert payload["ready"] is False
    assert payload["semantic_models_loaded"] is False
    assert payload["warehouse_connection_ok"] is False

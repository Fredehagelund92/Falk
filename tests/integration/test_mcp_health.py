from __future__ import annotations

from app import mcp as mcp_app


class _HealthyConnection:
    def list_tables(self):
        return ["orders"]


class _FakeCore:
    bsl_models = {"orders": object()}
    ibis_connection = _HealthyConnection()


def test_mcp_health_check_reports_service_and_ready(monkeypatch):
    monkeypatch.setattr(mcp_app, "get_agent", lambda: _FakeCore())

    payload = mcp_app.health_check.fn()

    assert payload["service"] == "mcp"
    assert payload["ready"] is True
    assert payload["semantic_models_loaded"] is True
    assert payload["warehouse_connection_ok"] is True

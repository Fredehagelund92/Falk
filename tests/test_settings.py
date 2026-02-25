from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from falk.settings import (
    ProjectRootNotFoundError,
    load_settings,
)


def _write_project(tmp_path: Path, config: dict) -> None:
    (tmp_path / "falk_project.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    (tmp_path / "semantic_models.yaml").write_text(
        "semantic_models: []\n", encoding="utf-8"
    )


def test_load_settings_uses_project_root(monkeypatch, tmp_path: Path):
    _write_project(
        tmp_path,
        {
            "agent": {"provider": "openai", "model": "gpt-5-mini"},
            "connection": {"type": "duckdb", "database": "data/warehouse.duckdb"},
        },
    )
    monkeypatch.setattr("falk.settings._find_project_root", lambda: tmp_path)

    settings = load_settings()

    assert settings.project_root == tmp_path
    assert settings.bsl_models_path == (tmp_path / "semantic_models.yaml").resolve()
    assert settings.agent.provider == "openai"
    assert settings.connection["type"] == "duckdb"


def test_load_settings_parses_access_policies(monkeypatch, tmp_path: Path):
    _write_project(
        tmp_path,
        {
            "agent": {"provider": "openai", "model": "gpt-5-mini"},
            "access_policies": {
                "default_role": "viewer",
                "roles": {"viewer": {"metrics": ["revenue"], "dimensions": ["date"]}},
                "users": [{"user_id": "alice@company.com", "roles": ["viewer"]}],
            },
        },
    )
    monkeypatch.setattr("falk.settings._find_project_root", lambda: tmp_path)

    settings = load_settings()

    assert settings.access.default_role == "viewer"
    assert settings.access.roles["viewer"].metrics == ["revenue"]
    assert settings.access.users[0].user_id == "alice@company.com"


def test_load_settings_parses_slack_policy(monkeypatch, tmp_path: Path):
    _write_project(
        tmp_path,
        {
            "agent": {"provider": "openai", "model": "gpt-5-mini"},
            "slack": {
                "exports_dm_only": True,
                "export_channel_allowlist": ["C123", "G123"],
                "export_block_message": "Use DM for exports.",
            },
        },
    )
    monkeypatch.setattr("falk.settings._find_project_root", lambda: tmp_path)

    settings = load_settings()

    assert settings.slack.exports_dm_only is True
    assert settings.slack.export_channel_allowlist == ["C123", "G123"]
    assert settings.slack.export_block_message == "Use DM for exports."


def test_load_settings_parses_memory_config(monkeypatch, tmp_path: Path):
    _write_project(
        tmp_path,
        {
            "agent": {"provider": "openai", "model": "gpt-5-mini"},
            "memory": {"enabled": True, "provider": "hindsight"},
        },
    )
    monkeypatch.setattr("falk.settings._find_project_root", lambda: tmp_path)

    settings = load_settings()

    assert settings.memory.enabled is True
    assert settings.memory.provider == "hindsight"


def test_load_settings_parses_extensions_tools(monkeypatch, tmp_path: Path):
    _write_project(
        tmp_path,
        {
            "agent": {
                "provider": "openai",
                "model": "gpt-5-mini",
                "extensions": {
                    "tools": [
                        "project_tools.customer_health",
                        {"module": "project_tools.forecasting", "enabled": True},
                        {"module": "project_tools.alerts", "enabled": False},
                    ],
                },
            },
        },
    )
    monkeypatch.setattr("falk.settings._find_project_root", lambda: tmp_path)

    settings = load_settings()

    assert len(settings.agent.extensions_tools) == 3
    assert settings.agent.extensions_tools[0].module == "project_tools.customer_health"
    assert settings.agent.extensions_tools[0].enabled is True
    assert settings.agent.extensions_tools[1].module == "project_tools.forecasting"
    assert settings.agent.extensions_tools[1].enabled is True
    assert settings.agent.extensions_tools[2].module == "project_tools.alerts"
    assert settings.agent.extensions_tools[2].enabled is False


def test_load_settings_extensions_tools_default_empty(monkeypatch, tmp_path: Path):
    _write_project(
        tmp_path,
        {"agent": {"provider": "openai", "model": "gpt-5-mini"}},
    )
    monkeypatch.setattr("falk.settings._find_project_root", lambda: tmp_path)

    settings = load_settings()

    assert settings.agent.extensions_tools == []


def test_load_settings_parses_session_config(monkeypatch, tmp_path: Path):
    _write_project(
        tmp_path,
        {
            "agent": {"provider": "openai", "model": "gpt-5-mini"},
            "session": {
                "store": "postgres",
                "postgres_url": "postgresql://local:5432/db",
                "schema": "falk_session",
                "ttl": 7200,
                "maxsize": 100,
            },
        },
    )
    monkeypatch.setattr("falk.settings._find_project_root", lambda: tmp_path)

    settings = load_settings()

    assert settings.session.store == "postgres"
    assert settings.session.postgres_url == "postgresql://local:5432/db"
    assert settings.session.schema == "falk_session"
    assert settings.session.ttl == 7200
    assert settings.session.maxsize == 100


def test_load_settings_falk_project_root_env(monkeypatch, tmp_path: Path):
    """FALK_PROJECT_ROOT env override resolves project root and bsl_models_path."""
    _write_project(
        tmp_path,
        {
            "agent": {"provider": "openai", "model": "gpt-5-mini"},
            "connection": {"type": "duckdb", "database": "data/warehouse.duckdb"},
        },
    )
    monkeypatch.delenv("FALK_PROJECT_ROOT", raising=False)
    monkeypatch.setenv("FALK_PROJECT_ROOT", str(tmp_path))

    settings = load_settings()

    assert settings.project_root == tmp_path.resolve()
    assert settings.bsl_models_path == (tmp_path / "semantic_models.yaml").resolve()
    assert settings.agent.provider == "openai"


def test_load_settings_falk_project_root_invalid_raises(monkeypatch, tmp_path: Path):
    """FALK_PROJECT_ROOT pointing to non-project dir raises ProjectRootNotFoundError."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.delenv("FALK_PROJECT_ROOT", raising=False)
    monkeypatch.setenv("FALK_PROJECT_ROOT", str(empty_dir))

    with pytest.raises(ProjectRootNotFoundError) as exc_info:
        load_settings()

    assert "FALK_PROJECT_ROOT" in str(exc_info.value)
    assert "falk_project.yaml" in str(exc_info.value)


def test_load_settings_no_project_raises(monkeypatch, tmp_path: Path):
    """No project markers in cwd/parents raises ProjectRootNotFoundError (not semantic-model error)."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.delenv("FALK_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(empty_dir)

    with pytest.raises(ProjectRootNotFoundError) as exc_info:
        load_settings()

    assert "No falk project found" in str(exc_info.value)
    assert "falk_project.yaml" in str(exc_info.value)


def test_load_settings_parent_discovery(monkeypatch, tmp_path: Path):
    """Valid parent with falk_project.yaml => upward discovery works."""
    _write_project(
        tmp_path,
        {
            "agent": {"provider": "openai", "model": "gpt-5-mini"},
            "connection": {"type": "duckdb", "database": "data/warehouse.duckdb"},
        },
    )
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.delenv("FALK_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(subdir)

    settings = load_settings()

    assert settings.project_root == tmp_path.resolve()
    assert settings.bsl_models_path == (tmp_path / "semantic_models.yaml").resolve()

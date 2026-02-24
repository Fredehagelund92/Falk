"""Tests for custom tool extensions (agent.extensions.tools)."""

from __future__ import annotations

from pathlib import Path

from falk.llm.tools import load_custom_toolsets
from falk.settings import ToolExtensionConfig


def test_load_custom_toolsets_empty_extensions(tmp_path: Path):
    """Empty extensions list returns no toolsets."""
    result = load_custom_toolsets(tmp_path, [])
    assert result == []


def test_load_custom_toolsets_skips_disabled(tmp_path: Path):
    """Disabled extensions are not loaded."""
    result = load_custom_toolsets(
        tmp_path,
        [ToolExtensionConfig(module="nonexistent.module", enabled=False)],
    )
    assert result == []


def test_load_custom_toolsets_missing_module_returns_empty(tmp_path: Path):
    """Missing module logs warning and returns no toolsets (fail-safe)."""
    result = load_custom_toolsets(
        tmp_path,
        [ToolExtensionConfig(module="nonexistent_module_xyz_123", enabled=True)],
    )
    assert result == []


def test_load_custom_toolsets_valid_module(tmp_path: Path):
    """Valid module exporting FunctionToolset is loaded."""
    # Create a minimal project_tools module
    tools_dir = tmp_path / "project_tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "sample.py").write_text(
        '''
"""Sample extension module for tests."""
from pydantic_ai import FunctionToolset, RunContext
from falk.agent import DataAgent

toolset = FunctionToolset()

@toolset.tool
def echo_metric(ctx: RunContext[DataAgent], name: str) -> str:
    """Echo a metric name (test tool)."""
    return f"echo:{name}"
''',
        encoding="utf-8",
    )

    result = load_custom_toolsets(
        tmp_path,
        [ToolExtensionConfig(module="project_tools.sample", enabled=True)],
    )

    assert len(result) == 1
    assert "echo_metric" in result[0].tools
    assert result[0].tools["echo_metric"].takes_ctx is True


def test_build_agent_includes_custom_toolsets(monkeypatch, tmp_path: Path):
    """build_agent merges custom toolsets when configured."""
    import sys

    import yaml

    # Use unique module name to avoid sys.modules cache from other tests
    ext_module = "project_tools_build_test"
    tools_dir = tmp_path / ext_module
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "ping_tool.py").write_text(
        '''
from pydantic_ai import FunctionToolset, RunContext
from falk.agent import DataAgent
toolset = FunctionToolset()
@toolset.tool
def ping(ctx: RunContext[DataAgent]) -> str:
    """Ping test."""
    return "pong"
''',
        encoding="utf-8",
    )

    (tmp_path / "falk_project.yaml").write_text(
        yaml.safe_dump(
            {
                "agent": {
                    "provider": "openai",
                    "model": "gpt-5-mini",
                    "extensions": {"tools": [f"{ext_module}.ping_tool"]},
                },
                "connection": {"type": "duckdb", "database": "data/warehouse.duckdb"},
                "paths": {"semantic_models": "semantic_models.yaml"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "semantic_models.yaml").write_text("models: {}\n", encoding="utf-8")

    monkeypatch.setattr("falk.settings._find_project_root", lambda: tmp_path)

    class _FakeDataAgent:
        bsl_models = {}
        metadata = {}

    captured_toolsets = []

    def _fake_agent(*args, toolsets=None, **kwargs):
        if toolsets is not None:
            captured_toolsets.extend(toolsets)
        return object()

    monkeypatch.setattr("falk.llm.builder.DataAgent", _FakeDataAgent)
    monkeypatch.setattr("falk.llm.builder.configure_observability", lambda: None)
    monkeypatch.setattr(
        "falk.llm.builder.build_system_prompt",
        lambda *a, **kw: "system prompt",
    )
    monkeypatch.setattr("falk.llm.builder.Agent", _fake_agent)

    from falk.llm import build_agent

    build_agent()

    tool_names = set()
    for tset in captured_toolsets:
        tool_names.update(tset.tools.keys())

    assert "ping" in tool_names, f"Expected ping in {tool_names}"
    assert "list_catalog" in tool_names  # built-in

    # Clean up sys.modules to avoid affecting other tests
    for mod in list(sys.modules.keys()):
        if mod == ext_module or mod.startswith(f"{ext_module}."):
            del sys.modules[mod]

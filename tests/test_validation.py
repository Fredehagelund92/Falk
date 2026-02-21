from __future__ import annotations

from pathlib import Path

import yaml

from falk.validation import _validate_config, validate_project


def test_validate_config_missing_file(tmp_path: Path):
    result = _validate_config(tmp_path)
    assert result.passed is False
    assert "falk_project.yaml" in result.message


def test_validate_project_minimal(tmp_path: Path):
    (tmp_path / "falk_project.yaml").write_text(
        yaml.safe_dump(
            {
                "project": {"name": "demo"},
                "agent": {"provider": "openai", "model": "gpt-5-mini"},
                "paths": {"semantic_models": "semantic_models.yaml"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "semantic_models.yaml").write_text("models: {}\n", encoding="utf-8")

    summary = validate_project(project_root=tmp_path, check_connection=False, check_agent=False)
    assert summary.results
    assert any(r.check_name == "Configuration" for r in summary.results)

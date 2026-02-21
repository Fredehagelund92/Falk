from __future__ import annotations

from pathlib import Path

from falk.evals.cases import discover_cases, load_cases
from falk.evals.runner import _sanitize_error


def test_load_cases_parses_user_id(tmp_path: Path):
    path = tmp_path / "cases.yaml"
    path.write_text(
        """
- name: access test
  question: What metrics are available?
  user_id: alice@company.com
  expected_tool: list_catalog
""".strip(),
        encoding="utf-8",
    )

    cases = load_cases(path)
    assert len(cases) == 1
    assert cases[0].user_id == "alice@company.com"
    assert cases[0].expect_tool == ["list_catalog"]


def test_discover_cases_loads_yaml_files(tmp_path: Path):
    (tmp_path / "a.yaml").write_text("- question: test a\n", encoding="utf-8")
    (tmp_path / "b.yml").write_text("- question: test b\n", encoding="utf-8")
    cases = discover_cases(tmp_path)
    assert len(cases) == 2


def test_sanitize_error_masks_sensitive_keys():
    msg = _sanitize_error("Authentication failed for api_key=sk-test-secret")
    assert "api_key" in msg.lower() or "authentication" in msg.lower()

from __future__ import annotations

import re

from typer.testing import CliRunner

from falk.cli import app

runner = CliRunner()


def test_cli_has_validate_command():
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0
    assert "Validate project configuration" in result.output


def test_cli_has_test_command():
    result = runner.invoke(app, ["test", "--help"])
    assert result.exit_code == 0
    assert "Run behavior evals" in result.output


def test_cli_has_access_test_command():
    result = runner.invoke(app, ["access-test", "--help"])
    assert result.exit_code == 0
    # Help formatting can vary by environment (ANSI styles, hard wraps).
    plain_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    normalized = re.sub(r"list-\s*users", "list-users", plain_output, flags=re.IGNORECASE)
    assert "list-users" in normalized.lower()


def test_cli_chat_command():
    """Chat command starts Pydantic AI web UI."""
    result = runner.invoke(app, ["chat", "--help"])
    assert result.exit_code == 0
    assert "web" in result.output.lower() or "8000" in result.output

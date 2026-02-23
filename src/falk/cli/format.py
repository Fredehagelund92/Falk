"""CLI formatting helpers — dbt-style layout, colors, and status display."""
from __future__ import annotations

import os
import sys

from rich.console import Console

from falk.validation import ValidationResult

_CONSOLE = Console(force_terminal=True)
_CONSOLE_ERR = Console(force_terminal=True, file=sys.stderr)
_CHECK_WIDTH = 50


def _use_color() -> bool:
    """Return False if NO_COLOR is set or stdout is not a TTY."""
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _format_check(name: str, status: str, width: int = _CHECK_WIDTH) -> str:
    """Build padded line like 'Configuration...................... [PASS]'."""
    status_str = f" [{status}]"
    padding_len = max(0, width - len(name) - len(status_str))
    return f"{name}{'.' * padding_len}{status_str}"


def print_check(
    result: ValidationResult,
    *,
    width: int = _CHECK_WIDTH,
    verbose: bool = False,
) -> None:
    """Emit one check line + details (always for failures, for passed only when verbose)."""
    if result.passed:
        status = "PASS"
        style = "green" if _use_color() else None
    elif result.warning:
        status = "WARN"
        style = "yellow" if _use_color() else None
    else:
        status = "FAIL"
        style = "red" if _use_color() else None

    line = _format_check(result.check_name, status, width=width)
    if style:
        _CONSOLE.print(line, style=style)
    else:
        _CONSOLE.print(line)

    show_details = (verbose or not result.passed) and result.details
    if show_details:
        detail_style = (
            "red" if (not result.passed and _use_color()) else ("dim" if _use_color() else None)
        )
        for detail in result.details:
            prefix = "  - "
            if detail_style:
                _CONSOLE.print(f"{prefix}{detail}", style=detail_style)
            else:
                _CONSOLE.print(f"{prefix}{detail}")


def print_section(title: str) -> None:
    """Print a section header."""
    _CONSOLE.print(f"\n=== {title} ===")


def print_info(msg: str) -> None:
    """Print an info line (plain or dim)."""
    if _use_color():
        _CONSOLE.print(msg, style="dim")
    else:
        _CONSOLE.print(msg)


def print_summary(passed: int, failed: int, warnings: int = 0) -> None:
    """Print compact summary line."""
    parts = [f"{passed} passed"]
    if failed:
        parts.append(f"{failed} failed")
    if warnings:
        parts.append(f"{warnings} warnings")
    line = ", ".join(parts)
    if failed and _use_color():
        _CONSOLE.print(line, style="red")
    else:
        _CONSOLE.print(line)


def print_status(status: str, message: str, *, err: bool = False) -> None:
    """Print a status line (for non-check contexts, e.g. errors)."""
    style = None
    if _use_color():
        if status == "PASS":
            style = "green"
        elif status == "FAIL":
            style = "red"
        elif status == "WARN":
            style = "yellow"
    line = f"[{status}] {message}"
    console = _CONSOLE_ERR if err else _CONSOLE
    if style:
        console.print(line, style=style)
    else:
        console.print(line)

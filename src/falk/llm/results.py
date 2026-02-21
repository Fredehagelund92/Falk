"""Shared helpers for tool result envelopes."""
from __future__ import annotations

from typing import Any


def tool_error(error: str, error_code: str = "TOOL_ERROR") -> dict[str, Any]:
    """Build a standard error envelope for tool responses."""
    return {"ok": False, "error": error, "error_code": error_code}


def is_tool_error(payload: Any) -> bool:
    """Return True when a payload is a standard tool error envelope."""
    return (
        isinstance(payload, dict)
        and payload.get("ok") is False
        and isinstance(payload.get("error"), str)
    )

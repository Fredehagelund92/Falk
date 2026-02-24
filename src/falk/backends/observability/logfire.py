"""Logfire-based observability backend.

Provides tracing (via instrument_pydantic_ai) and feedback recording.
If Logfire is not configured, all functions are no-ops.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_configured: bool = False


def configure() -> bool:
    """Configure Logfire and instrument Pydantic AI. Call once at process startup.

    Skips configuration when no token is present to avoid interactive prompts
    (e.g. in MCP stdio contexts where stdin is used for JSON-RPC).

    Returns True if Logfire was configured, False otherwise (no-op).
    """
    global _configured
    if _configured:
        return True

    if not (os.getenv("LOGFIRE_TOKEN") or os.getenv("LOGTAIL_TOKEN")):
        _configured = True
        return False

    try:
        import logfire

        logfire.configure(send_to_logfire="if-token-present")
        logfire.instrument_pydantic_ai()
        logger.info("Logfire configured and Pydantic AI instrumented")
        _configured = True
        return True
    except ImportError:
        logger.warning("Logfire env vars set but package not installed. Run: uv sync")
        _configured = True
        return False
    except Exception as e:
        logger.warning("Failed to configure Logfire: %s", e)
        _configured = True
        return False


def get_trace_id_from_context() -> str | None:
    """Get the current trace ID from OpenTelemetry context (e.g. after agent run).

    Call this in the same thread/context where the agent run completed.
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording() and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
    except Exception:
        pass
    return None


def record_feedback_event(
    trace_id: str | None,
    score: float | None = None,
    comment: str | None = None,
    user_id: str | None = None,
    **attrs: Any,
) -> None:
    """Record a feedback event (e.g. thumbs up/down) for a trace.

    If trace_id is None or Logfire is not configured, logs locally only.
    """
    if not trace_id:
        return

    try:
        import logfire

        logfire.info(
            "user_feedback",
            trace_id=trace_id,
            feedback_score=score,
            feedback_comment=comment,
            feedback_user_id=user_id,
            **attrs,
        )
    except Exception as e:
        logger.warning("Failed to record feedback to Logfire: %s", e)

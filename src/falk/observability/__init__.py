"""Observability and feedback collection for the agent.

Uses Logfire when configured (LOGFIRE_TOKEN or LOGTAIL_TOKEN).
All functions are no-ops or log-only when not configured.
"""

from falk.backends.observability.logfire import (
    configure as configure_observability,
)
from falk.backends.observability.logfire import (
    get_trace_id_from_context,
)
from falk.observability.feedback import record_feedback

__all__ = [
    "configure_observability",
    "get_trace_id_from_context",
    "record_feedback",
]

"""Observability and feedback collection for the agent.

This module provides optional tracing and feedback functionality through LangFuse.
All functions are no-ops if LangFuse is not configured.
"""
from falk.observability.feedback import record_feedback
from falk.observability.langfuse import get_langfuse_client, trace_agent_run

__all__ = [
    "get_langfuse_client",
    "trace_agent_run",
    "record_feedback",
]

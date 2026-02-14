"""LangFuse integration for observability, evaluation, and feedback.

This module provides optional LangFuse tracing and feedback collection.
If LangFuse is not configured (env vars not set), all functions are no-ops.

Usage::

    from falk.langfuse_integration import get_langfuse_client, trace_agent_run

    # In pydantic_agent.py
    langfuse = get_langfuse_client()
    if langfuse:
        trace = trace_agent_run(user_query, agent_result)
        # Feedback is recorded via record_feedback() which uses LangFuse
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Global client (initialized once)
_langfuse_client: Any = None


def get_langfuse_client():
    """Get LangFuse client if configured, None otherwise.

    Checks for LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY env vars.
    If not set, returns None (opt-in).
    """
    global _langfuse_client

    if _langfuse_client is not None:
        return _langfuse_client

    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    host = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").strip()

    if not secret_key or not public_key:
        logger.debug("LangFuse not configured (LANGFUSE_SECRET_KEY or LANGFUSE_PUBLIC_KEY not set)")
        _langfuse_client = False  # Mark as checked, don't retry
        return None

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            host=host,
        )
        logger.info("LangFuse client initialized")
        return _langfuse_client
    except ImportError:
        logger.warning(
            "LangFuse env vars set but package not installed. "
            "Run: uv sync"
        )
        _langfuse_client = False
        return None
    except Exception as e:
        logger.warning("Failed to initialize LangFuse: %s", e)
        _langfuse_client = False
        return None


def trace_agent_run(
    user_query: str,
    agent_result: Any,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    sync: bool = True,
) -> Any:
    """Create a LangFuse trace for an agent run.

    Args:
        user_query: The user's question/request.
        agent_result: Pydantic AI AgentResult object.
        user_id: Optional user identifier (Slack user ID, etc.).
        metadata: Optional metadata dict.
        sync: If True, flush immediately so data is sent before process exit.

    Returns:
        LangFuse trace object, or None if LangFuse not configured.
    """
    langfuse = get_langfuse_client()
    if not langfuse:
        return None

    try:
        trace = langfuse.trace(
            name="falk_query",
            user_id=user_id,
            metadata={
                "source": "slack" if user_id else "web",
                **(metadata or {}),
            },
        )

        # Extract model info from agent result
        model_name = "unknown"
        tokens_used = None
        cost = None
        
        # Pydantic AI stores model info in the result
        if hasattr(agent_result, "model_name"):
            model_name = agent_result.model_name
        elif hasattr(agent_result, "model"):
            model_name = str(agent_result.model)
        
        # Try to extract token usage if available
        if hasattr(agent_result, "tokens_used"):
            tokens_used = agent_result.tokens_used
        if hasattr(agent_result, "cost"):
            cost = agent_result.cost

        # Add the user query as a generation
        generation = trace.generation(
            name="agent_response",
            model=model_name,
            input=user_query,
            output=agent_result.output or "",
            metadata={
                "tokens_used": tokens_used,
                "cost": cost,
            },
        )

        # Add tool calls as spans (nested under the generation for better hierarchy)
        messages = agent_result.all_messages() if hasattr(agent_result, "all_messages") else []
        for msg in messages:
            for part in getattr(msg, "parts", []):
                if hasattr(part, "tool_name") and hasattr(part, "args"):
                    tool_args = part.args if isinstance(part.args, dict) else {}
                    # Get tool result if available
                    tool_result = getattr(part, "result", None)
                    # Create span as child of generation
                    generation.span(
                        name=f"tool_{part.tool_name}",
                        input=tool_args,
                        output=str(tool_result)[:500] if tool_result else None,  # Truncate long outputs
                        metadata={"tool": part.tool_name},
                    )

        if sync:
            langfuse.flush()
        return trace
    except Exception as e:
        logger.warning("Failed to create LangFuse trace: %s", e)
        return None


def record_feedback_to_langfuse(
    trace_id: str | None,
    score: float | None = None,
    comment: str | None = None,
    user_id: str | None = None,
    sync: bool = True,
) -> None:
    """Record feedback to LangFuse trace.

    Args:
        trace_id: LangFuse trace ID (from trace_agent_run).
        score: Feedback score (1.0 for positive, 0.0 for negative, or custom).
        comment: Optional feedback comment.
        user_id: Optional user identifier.
        sync: If True, flush immediately so data is sent before process exit.
    """
    langfuse = get_langfuse_client()
    if not langfuse or not trace_id:
        return

    try:
        langfuse.score(
            trace_id=trace_id,
            name="user_feedback",
            value=score,
            comment=comment,
            user_id=user_id,
        )
        if sync:
            langfuse.flush()
    except Exception as e:
        logger.warning("Failed to record LangFuse feedback: %s", e)


"""Feedback collection for agent improvement.

Records user feedback (thumbs up/down) from Slack interactions to LangFuse.
If LangFuse is not configured, feedback is logged for visibility but not persisted.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def record_feedback(
    user_query: str,
    agent_response: str,
    feedback: str,  # "positive" or "negative"
    user_id: str | None = None,
    channel: str | None = None,
    thread_ts: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    langfuse_trace_id: str | None = None,
    langfuse_sync: bool = True,
) -> None:
    """Record feedback to LangFuse.

    If LangFuse is not configured, feedback is logged but not persisted.
    Set up LangFuse for full feedback tracking and evaluation.

    Args:
        user_query: The user's original question/request.
        agent_response: The agent's response text (truncated to 500 chars).
        feedback: ``"positive"`` or ``"negative"``.
        user_id: Slack user ID (optional).
        channel: Slack channel ID (optional).
        thread_ts: Slack thread timestamp (optional).
        tool_calls: Tool calls the agent made during this interaction.
        metadata: Additional metadata.
        langfuse_trace_id: LangFuse trace ID (if available from agent run).
    """
    tools_used = ""
    if tool_calls:
        tools_used = ", ".join(tc.get("tool", "") for tc in tool_calls)

    # Send to LangFuse if configured
    if langfuse_trace_id:
        try:
            from falk.langfuse_integration import record_feedback_to_langfuse

            score = 1.0 if feedback == "positive" else 0.0
            comment = f"User feedback: {feedback}"
            if tools_used:
                comment += f" | Tools used: {tools_used}"

            record_feedback_to_langfuse(
                trace_id=langfuse_trace_id,
                score=score,
                comment=comment,
                user_id=user_id,
                sync=langfuse_sync,
            )
            logger.info(
                "Recorded %s feedback to LangFuse (trace=%s, user=%s)",
                feedback, langfuse_trace_id, user_id,
            )
            return
        except Exception as e:
            logger.warning("Failed to record feedback to LangFuse: %s", e)

    # No LangFuse — just log it
    logger.info(
        "Feedback: %s | user=%s | query=%s | tools=%s",
        feedback, user_id, user_query[:80], tools_used,
    )

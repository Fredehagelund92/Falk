"""Feedback collection for agent improvement.

Records user feedback (thumbs up/down) from Slack interactions.
Uses Logfire when configured; otherwise logs locally.
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
    trace_id: str | None = None,
    sync: bool = True,
) -> None:
    """Record feedback for an agent run.

    If trace_id is provided and Logfire is configured, feedback is sent to Logfire.
    Otherwise feedback is logged locally.

    Args:
        user_query: The user's original question/request.
        agent_response: The agent's response text (truncated to 500 chars).
        feedback: "positive" or "negative".
        user_id: Slack user ID (optional).
        channel: Slack channel ID (optional).
        thread_ts: Slack thread timestamp (optional).
        tool_calls: Tool calls the agent made during this interaction.
        metadata: Additional metadata.
        trace_id: Trace ID from the agent run (for Logfire linking).
        sync: Unused, kept for API compatibility.
    """
    tools_used = ""
    if tool_calls:
        tools_used = ", ".join(tc.get("tool", "") for tc in tool_calls)

    if trace_id:
        try:
            from falk.backends.observability.logfire import record_feedback_event

            score = 1.0 if feedback == "positive" else 0.0
            comment = f"User feedback: {feedback}"
            if tools_used:
                comment += f" | Tools used: {tools_used}"

            record_feedback_event(
                trace_id=trace_id,
                score=score,
                comment=comment,
                user_id=user_id,
            )
            logger.info(
                "Recorded %s feedback (trace=%s, user=%s)",
                feedback,
                trace_id,
                user_id,
            )
            return
        except Exception as e:
            logger.warning("Failed to record feedback: %s", e)

    logger.info(
        "Feedback: %s | user=%s | query=%s | tools=%s",
        feedback,
        user_id,
        user_query[:80],
        tools_used,
    )

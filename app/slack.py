"""Slack bot for the data agent.

Run in socket mode (easiest for development)::

    python app/slack.py

Requires environment variables:

    SLACK_BOT_TOKEN   — Bot User OAuth Token (xoxb-...)
    SLACK_APP_TOKEN   — App-Level Token (xapp-...) with ``connections:write`` scope
    LLM_API_KEY       — API key for your chosen LLM provider:
                        - OPENAI_API_KEY (for OpenAI models)
                        - ANTHROPIC_API_KEY (for Anthropic Claude)
                        - GOOGLE_API_KEY (for Google Gemini)
                        - etc.

See README.md for full setup instructions.
"""
from __future__ import annotations

import logging
import os
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env before importing falk (needs LLM API keys)
_env_candidates = [Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"]
for _p in _env_candidates:
    if _p.exists():
        load_dotenv(_p, override=True)
        break
else:
    load_dotenv(override=True)

from slack_bolt import App  # noqa: E402
from slack_bolt.adapter.socket_mode import SocketModeHandler  # noqa: E402

from falk import build_agent  # noqa: E402
from falk.feedback import record_feedback  # noqa: E402
from falk.settings import load_settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("falk.slack")

# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

bolt = App(token=os.environ["SLACK_BOT_TOKEN"])
agent = build_agent()

# ---------------------------------------------------------------------------
# Thread-based conversation memory
# ---------------------------------------------------------------------------
# Each Slack thread gets its own Pydantic AI message_history so follow-ups
# like "break that down by country" work naturally.
#
# Scaling note: this is in-memory, fine for a single process.
# For multi-process deployments, swap this for Redis.

MAX_THREADS = 200

_thread_history: OrderedDict[str, list] = OrderedDict()

# ---------------------------------------------------------------------------
# Feedback tracking
# ---------------------------------------------------------------------------
# Track user queries and responses so we can record feedback when users react.
# Maps message_ts -> context dict

_message_context: dict[str, dict[str, Any]] = {}


def _store_history(thread_ts: str, messages: list):
    """Store conversation history for a thread, evicting oldest if full."""
    _thread_history[thread_ts] = messages
    _thread_history.move_to_end(thread_ts)
    while len(_thread_history) > MAX_THREADS:
        _thread_history.popitem(last=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_mention(text: str) -> str:
    """Remove ``<@BOT_ID>`` from message text."""
    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()


def _extract_tool_calls(messages: list) -> list[dict[str, Any]]:
    """Extract tool call info from Pydantic AI message history."""
    calls: list[dict[str, Any]] = []
    for msg in messages:
        for part in getattr(msg, "parts", []):
            if hasattr(part, "tool_name") and hasattr(part, "args"):
                calls.append({
                    "tool": part.tool_name,
                    "args": part.args if isinstance(part.args, dict) else {},
                })
    return calls


# ---------------------------------------------------------------------------
# Agent handler
# ---------------------------------------------------------------------------

def _upload_pending_files(client, channel: str, thread_ts: str | None):
    """Upload any files the agent produced (CSV, Excel, charts) to Slack."""
    files: list[dict[str, Any]] = getattr(agent, "_pending_files", None) or []
    if not files:
        return

    for f in list(files):
        filepath = Path(f["path"])
        if not filepath.exists():
            logger.warning("Pending file not found: %s", filepath)
            continue
        try:
            client.files_upload_v2(
                channel=channel,
                file=str(filepath),
                filename=f.get("title") or filepath.name,
                title=f.get("title") or filepath.name,
                thread_ts=thread_ts,
                initial_comment="",
            )
            logger.info("Uploaded %s to channel %s", filepath.name, channel)
        except Exception:
            logger.warning("Failed to upload %s", filepath.name, exc_info=True)

    files.clear()


def _handle(text: str, say, client, thread_ts: str | None = None, user_id: str | None = None, channel: str | None = None):
    """Run the agent and post the reply."""
    if not text:
        say("Hey! Ask me a data question :wave:", thread_ts=thread_ts)
        return

    # Acknowledge so the user knows we're working on it
    say("_Thinking..._", thread_ts=thread_ts)

    # Retrieve conversation history for this thread (if any)
    history = _thread_history.get(thread_ts) if thread_ts else None

    tool_calls: list[dict[str, Any]] = []
    langfuse_trace_id: str | None = None
    langfuse_sync: bool = True
    try:
        result = agent.run_sync(
            text,
            message_history=history or None,
            user_id=user_id,
            metadata={"interface": "slack"},
        )
        reply = result.output or "I couldn't generate a response — try rephrasing?"
        tool_calls = _extract_tool_calls(result.all_messages())
        # Create LangFuse trace when enabled
        settings = load_settings()
        langfuse_ext = settings.extensions.get("langfuse")
        langfuse_sync = (
            langfuse_ext.settings.get("sync", True)
            if langfuse_ext and langfuse_ext.enabled
            else True
        )
        if langfuse_ext and langfuse_ext.enabled:
            from falk.langfuse_integration import trace_agent_run

            trace = trace_agent_run(text, result, user_id=user_id, sync=langfuse_sync)
            if trace and hasattr(trace, "id"):
                langfuse_trace_id = trace.id

        # Persist conversation for follow-ups
        if thread_ts:
            _store_history(thread_ts, result.all_messages())
    except Exception:
        logger.exception("Agent error")
        reply = "Something went wrong — please try again in a moment."

    # Post reply and store context for feedback tracking
    try:
        if channel:
            # Add subtle feedback hint (only for substantive responses)
            reply_with_hint = reply
            if len(reply) > 100 and not reply.endswith("_"):
                reply_with_hint = reply + "\n\n_React with :thumbsup: or :thumbsdown: to rate this response_"

            response = client.chat_postMessage(
                channel=channel,
                text=reply_with_hint,
                thread_ts=thread_ts,
            )
            message_ts = response.get("ts") if response else None

            # Upload any files the agent produced (CSV, Excel, charts)
            _upload_pending_files(client, channel, thread_ts)

            if message_ts:
                _message_context[message_ts] = {
                    "user_query": text,
                    "agent_response": reply,
                    "tool_calls": tool_calls,
                    "user_id": user_id,
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "langfuse_trace_id": langfuse_trace_id,
                    "langfuse_sync": langfuse_sync,
                }
                # Clean up old entries (keep last 1000)
                if len(_message_context) > 1000:
                    oldest = min(_message_context.keys())
                    _message_context.pop(oldest, None)
        else:
            say(reply, thread_ts=thread_ts)
    except Exception:
        logger.warning("Failed to use client.chat_postMessage, falling back to say()")
        say(reply, thread_ts=thread_ts)


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

@bolt.event("app_mention")
def handle_mention(event, say, client):
    """Respond when the bot is ``@mentioned`` in a channel."""
    text = _strip_mention(event.get("text", ""))
    thread_ts = event.get("thread_ts") or event.get("ts")
    user_id = event.get("user")
    channel = event.get("channel")
    _handle(text, say, client, thread_ts=thread_ts, user_id=user_id, channel=channel)


@bolt.event("message")
def handle_dm(event, say, client):
    """Respond to direct messages (DMs)."""
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id"):
        return
    text = (event.get("text") or "").strip()
    user_id = event.get("user")
    channel = event.get("channel")
    _handle(text, say, client, user_id=user_id, channel=channel)


# ---------------------------------------------------------------------------
# Feedback — emoji reactions → LangFuse
# ---------------------------------------------------------------------------

# Positive reactions (👍) -> recorded in LangFuse as score=1.0
# Negative reactions (👎) -> recorded in LangFuse as score=0.0
# Data team reviews feedback in LangFuse dashboard and adds corrections there.

_POSITIVE_REACTIONS = frozenset({
    "thumbsup", "+1", "white_check_mark", "heart", "fire", "100",
})
_NEGATIVE_REACTIONS = frozenset({
    "thumbsdown", "-1", "x", "disappointed", "confused",
})


@bolt.event("reaction_added")
def handle_reaction(event):
    """Record feedback when users react with thumbsup/thumbsdown."""
    reaction = event.get("reaction", "")
    message_ts = event.get("item", {}).get("ts")
    user_id = event.get("user")

    if not message_ts or message_ts not in _message_context:
        return

    if reaction in _POSITIVE_REACTIONS:
        feedback_type = "positive"
    elif reaction in _NEGATIVE_REACTIONS:
        feedback_type = "negative"
    else:
        return

    context = _message_context[message_ts]

    record_feedback(
        user_query=context["user_query"],
        agent_response=context["agent_response"],
        feedback=feedback_type,
        user_id=user_id,
        channel=context.get("channel"),
        thread_ts=context.get("thread_ts"),
        tool_calls=context.get("tool_calls"),
        langfuse_trace_id=context.get("langfuse_trace_id"),
        langfuse_sync=context.get("langfuse_sync", True),
    )

    logger.info("Recorded %s feedback from user %s", feedback_type, user_id)


# ---------------------------------------------------------------------------
# Entry point — socket mode
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    handler = SocketModeHandler(bolt, os.environ["SLACK_APP_TOKEN"])
    print("Data Agent is running in Slack (socket mode)")
    print("   Press Ctrl+C to stop\n")
    handler.start()

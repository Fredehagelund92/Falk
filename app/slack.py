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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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

from pydantic_ai import UsageLimitExceeded, UsageLimits  # noqa: E402

from falk import build_agent  # noqa: E402
from falk.agent import DataAgent  # noqa: E402
from falk.llm import get_pending_files_for_session, clear_pending_files_for_session  # noqa: E402
from falk.llm.memory import retain_interaction_sync  # noqa: E402
from falk.observability import get_trace_id_from_context, record_feedback  # noqa: E402
from falk.settings import load_settings  # noqa: E402
from falk.slack import can_deliver_exports, format_reply_for_slack  # noqa: E402

APP_SETTINGS = load_settings()
QUERY_TIMEOUT = max(5, int(APP_SETTINGS.advanced.slack_run_timeout_seconds))
_LOG_LEVEL = str(APP_SETTINGS.advanced.log_level).upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("falk.slack")

# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

bolt = App(token=os.environ["SLACK_BOT_TOKEN"])

# Initialize DataAgent once at startup (shared across all queries)
try:
    core_agent = DataAgent(settings=APP_SETTINGS)
    logger.info(f"DataAgent initialized with {len(core_agent.bsl_models)} semantic models")
except Exception as e:
    logger.error(f"Failed to initialize DataAgent: {e}")
    raise RuntimeError(
        f"Cannot start Slack bot - DataAgent initialization failed: {e}\n"
        "Check your falk_project.yaml, semantic_models.yaml, and database connection."
    ) from e

agent = build_agent()

# ---------------------------------------------------------------------------
# Thread-based conversation memory
# ---------------------------------------------------------------------------
# Each Slack thread gets its own Pydantic AI message_history so follow-ups
# like "break that down by country" work naturally.
#
# Scaling note: this is in-memory, fine for a single process.
# Session state (last query, pending files) uses Postgres when POSTGRES_URL is set.

MAX_THREADS = 200

_thread_history: OrderedDict[str, list] = OrderedDict()

# ---------------------------------------------------------------------------
# Feedback tracking
# ---------------------------------------------------------------------------
# Track user queries and responses so we can record feedback when users react.
# Maps message_ts -> context dict

_message_context: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# User identity — resolve Slack user ID to email for access control
# ---------------------------------------------------------------------------
# Access policies in falk_project.yaml use email addresses (e.g. alice@company.com)
# because they are human-readable and easy to maintain.  Here we resolve the
# opaque Slack user_id (e.g. U012ABC34) that arrives in event payloads to the
# user's profile email via the Slack users.info API, then cache the result so
# we only hit the API once per user per process lifetime.
#
# Requires the `users:read` OAuth scope (already needed for most Slack bots).
# Falls back to the raw Slack user_id if the API call fails or returns no email,
# so existing deployments without access_policies configured are unaffected.

_user_email_cache: dict[str, str] = {}  # slack_user_id -> email


def _resolve_user_email(client, slack_user_id: str) -> str | None:
    """Return the email address for a Slack user_id, with in-process caching.

    Returns None if the lookup fails or the profile has no email set.
    Requires the ``users:read`` OAuth scope on the bot token.
    """
    if slack_user_id in _user_email_cache:
        return _user_email_cache[slack_user_id]
    try:
        resp = client.users_info(user=slack_user_id)
        email: str | None = (
            (resp.get("user") or {})
            .get("profile", {})
            .get("email")
        )
        if email:
            _user_email_cache[slack_user_id] = email
            logger.debug("Resolved %s -> %s", slack_user_id, email)
        return email
    except Exception:
        logger.debug("Could not resolve email for Slack user %s", slack_user_id, exc_info=True)
        return None


def _identity(client, slack_user_id: str | None) -> str | None:
    """Return the access-control identity for a Slack user.

    Prefers the user's email address (matches falk_project.yaml access_policies).
    Falls back to the raw Slack user_id so that policies using legacy Slack IDs
    continue to work.  Returns None if no user is known.
    """
    if not slack_user_id:
        return None
    return _resolve_user_email(client, slack_user_id) or slack_user_id


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

def _upload_pending_files(client, channel: str, thread_ts: str | None, session_id: str) -> str:
    """Upload any files the agent produced (CSV, Excel, charts) to Slack.

    Returns one of: "uploaded", "blocked", "none".
    """
    files = get_pending_files_for_session(session_id)
    if not files:
        return "none"

    if not can_deliver_exports(channel, APP_SETTINGS.slack):
        clear_pending_files_for_session(session_id)
        return "blocked"

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

    clear_pending_files_for_session(session_id)
    return "uploaded"


def _handle(text: str, say, client, thread_ts: str | None = None, user_id: str | None = None, channel: str | None = None):
    """Run the agent and post the reply."""
    if not text:
        say("Hey! Ask me a data question :wave:", thread_ts=thread_ts)
        return

    # Resolve email for access control. Policies in falk_project.yaml use emails
    # (alice@company.com). Falls back to raw Slack user_id if unavailable.
    identity = _identity(client, user_id)

    # Post "Thinking..." and get ts so we can replace it with the reply (cleaner threads)
    thinking_ts: str | None = None
    if channel:
        try:
            resp = client.chat_postMessage(
                channel=channel,
                text="_Thinking..._",
                thread_ts=thread_ts,
            )
            thinking_ts = resp.get("ts") if resp else None
        except Exception:
            pass
    if not thinking_ts:
        say("_Thinking..._", thread_ts=thread_ts)

    # Retrieve conversation history for this thread (if any)
    history = _thread_history.get(thread_ts) if thread_ts else None

    tool_calls: list[dict[str, Any]] = []
    trace_id: str | None = None

    def _run_and_capture_trace():
        result = agent.run_sync(
            text,
            message_history=history or None,
            deps=core_agent,
            usage_limits=UsageLimits(
                request_limit=APP_SETTINGS.advanced.request_limit,
                tool_calls_limit=APP_SETTINGS.advanced.tool_calls_limit,
            ),
            metadata={
                "interface": "slack",
                "user_id": identity,
                "thread_ts": thread_ts,
                "channel": channel,
            },
        )
        tid = get_trace_id_from_context()
        return result, tid

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run_and_capture_trace)
            try:
                result, trace_id = future.result(timeout=QUERY_TIMEOUT)
            except FuturesTimeoutError:
                reply = (
                    "That request took too long. Try a simpler question or try again in a moment. "
                    "If this happens often, ask your admin to increase the timeout settings."
                )
            else:
                reply = result.output or "I couldn't generate a response — try rephrasing?"
                tool_calls = _extract_tool_calls(result.all_messages())
                if thread_ts:
                    _store_history(thread_ts, result.all_messages())
                sid = thread_ts or (f"{channel}:{user_id}" if user_id else "default")
                retain_interaction_sync(
                    session_id=sid,
                    user_id=identity,
                    query=text,
                    response=reply,
                    tool_calls=tool_calls,
                    enabled=APP_SETTINGS.memory.enabled,
                    provider=APP_SETTINGS.memory.provider,
                )
    except FuturesTimeoutError:
        reply = (
            "That request took too long. Try a simpler question or try again in a moment. "
            "If this happens often, ask your admin to increase the timeout settings."
        )
    except UsageLimitExceeded:
        reply = (
            "That query used too many steps. Try a simpler or more focused question."
        )
    except Exception:
        logger.exception("Agent error")
        reply = "Something went wrong — please try again in a moment."

    # Format reply and update the Thinking message (or post new if update fails)
    reply_formatted, blocks = format_reply_for_slack(
        reply,
        user_id=user_id,
        channel=channel,
        thread_ts=thread_ts,
    )

    try:
        if channel and thinking_ts:
            # Replace Thinking message with the reply (cleaner — no extra message)
            update_kwargs = {
                "channel": channel,
                "ts": thinking_ts,
                "text": reply_formatted[:4000],
            }
            if blocks:
                update_kwargs["blocks"] = blocks
            try:
                response = client.chat_update(**update_kwargs)
                message_ts = response.get("ts") if response else thinking_ts
            except Exception:
                # Fallback: post as new message if update fails (e.g. message too old)
                post_kwargs = {
                    "channel": channel,
                    "text": reply_formatted[:4000],
                    "thread_ts": thread_ts,
                }
                if blocks:
                    post_kwargs["blocks"] = blocks
                response = client.chat_postMessage(**post_kwargs)
                message_ts = response.get("ts") if response else None
        elif channel:
            post_kwargs = {
                "channel": channel,
                "text": reply_formatted[:4000],
                "thread_ts": thread_ts,
            }
            if blocks:
                post_kwargs["blocks"] = blocks
            response = client.chat_postMessage(**post_kwargs)
            message_ts = response.get("ts") if response else None
        else:
            say(reply_formatted, thread_ts=thread_ts)
            message_ts = None

        # Upload any files the agent produced (CSV, Excel, charts)
        if channel:
            session_id = thread_ts or f"{channel}:{user_id}" if user_id else "default"
            upload_state = _upload_pending_files(client, channel, thread_ts, session_id)
            if upload_state == "blocked":
                client.chat_postMessage(
                    channel=channel,
                    text=APP_SETTINGS.slack.export_block_message,
                    thread_ts=thread_ts,
                )

        if message_ts and channel:
            _message_context[message_ts] = {
                "user_query": text,
                "agent_response": reply,
                "tool_calls": tool_calls,
                "user_id": identity,
                "channel": channel,
                "thread_ts": thread_ts,
                "trace_id": trace_id,
            }
            if len(_message_context) > 1000:
                oldest = min(_message_context.keys())
                _message_context.pop(oldest, None)
    except Exception:
        logger.warning("Failed to post reply, falling back to say()")
        say(reply_formatted, thread_ts=thread_ts)


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


@bolt.command("/falk")
def handle_slash_command(ack, command, client):
    """Handle /falk <question> — query without @mentioning the bot."""
    ack()  # Must respond within 3 seconds
    text = (command.get("text") or "").strip()
    channel = command.get("channel_id")
    user_id = command.get("user_id")
    if not channel or not user_id:
        return
    # Use say that posts to channel; _handle needs client for chat_postMessage/update
    def _say(msg, thread_ts=None):
        client.chat_postMessage(channel=channel, text=msg, thread_ts=thread_ts)

    _handle(text, _say, client, thread_ts=None, user_id=user_id, channel=channel)


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
        trace_id=context.get("trace_id"),
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

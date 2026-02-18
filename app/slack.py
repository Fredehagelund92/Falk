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
from falk.observability import record_feedback  # noqa: E402
from falk.settings import load_settings  # noqa: E402

APP_SETTINGS = load_settings()
QUERY_TIMEOUT = max(5, int(APP_SETTINGS.advanced.query_timeout_seconds))
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


def _markdown_to_mrkdwn(text: str) -> str:
    """Convert Markdown to Slack mrkdwn format.
    
    - Bullets: `- item` or `* item` → `• item`
    - Numbered: `1. item` → `• item`
    - Bold: `**text**` or `__text__` → `*text*`
    - Italic: `*text*` → `_text_`
    - Links: `[text](url)` → `<url|text>`
    - Headings: `# text` → `*text*`
    - Code: `` `code` `` → `` `code` ``
    - Code blocks: ``` preserved
    - Blockquotes: `> text` → `> text`
    - Strikethrough: `~~text~~` → `~text~`
    - HTML entities: `&amp;` → `&`
    """
    import html
    
    if not text:
        return ""

    try:
        text = text.strip()
        
        # Unescape HTML entities if LLM outputs them
        text = html.unescape(text)
        
        # Track if we're inside a code block (skip conversion)
        in_code_block = False
        lines = []
        
        for line in text.split("\n"):
            # Code block delimiters
            if re.match(r"^```\s*\w*\s*$", line.strip()) or line.strip() == "```":
                in_code_block = not in_code_block
                lines.append(line)
                continue
            
            # Skip conversion inside code blocks
            if in_code_block:
                lines.append(line)
                continue
            
            # Italic: *text* → _text_ (do BEFORE heading/bold conversion)
            line = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"_\1_", line)
            
            # Bullets: - or * or • → • (after italic so * doesn't interfere)
            line = re.sub(r"^(\s*)([-\u2022]\s+)(.+)", r"\1• \3", line)
            
            # Numbered lists: 1. 2. 3. → •
            line = re.sub(r"^(\s*)(\d+)\.\s+(.+)", r"\1• \3", line)
            
            # Headings: # text → *text*
            line = re.sub(r"^#{1,6}\s+(.+?)\s*$", r"*\1*", line)
            
            # Blockquotes (preserve)
            # Already in correct format: > text
            
            lines.append(line)
        
        result = "\n".join(lines)
        
        # Bold: **text** or __text__ → *text* (single-line only)
        result = re.sub(r"(?<!\*)\*\*([^\n]+?)\*\*(?!\*)", r"*\1*", result)
        result = re.sub(r"__([^\n]+?)__", r"*\1*", result)
        
        # Links: [text](url) → <url|text>
        result = re.sub(r"\[(.+?)\]\((.+?)\)", r"<\2|\1>", result)
        
        # Strikethrough: ~~text~~ → ~text~
        result = re.sub(r"~~(.+?)~~", r"~\1~", result)
        
        # Inline code: `code` (already correct format)
        # No conversion needed
        
        # Clean up orphaned ** at end (truncated text)
        result = re.sub(r"\*\*\s*$", "", result)
        
        return result.strip()
        
    except Exception as e:
        logging.error("Markdown conversion error: %s", e)
        return text


def _strip_file_paths(text: str) -> str:
    """Remove full file paths from messages — files are uploaded to Slack."""
    # [here](C:\path\to\file.csv) → "the file is attached above"
    def _replace_link(match) -> str:
        link_text, url = match.group(1), match.group(2)
        if any(url.rstrip().lower().endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".gif")):
            return "in the attachment above"
        return match.group(0)

    text = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", _replace_link, text)
    # Bare paths → just filename
    text = re.sub(
        r"[A-Za-z]:\\[^\s]+\.(csv|xlsx|xls|png|jpg|jpeg|gif)\b",
        lambda m: Path(m.group(0)).name,
        text,
    )
    return text


def _parse_rich_text_elements(text: str) -> list[dict[str, Any]]:
    """Parse text with mrkdwn formatting into rich_text elements with styles.
    
    Handles: *bold*, _italic_, ~strikethrough~, `code`
    """
    elements = []
    pos = 0
    
    # Pattern: *bold* or _italic_ or ~strike~ or `code`
    pattern = re.compile(r'(\*[^*\n]+?\*|_[^_\n]+?_|~[^~\n]+?~|`[^`\n]+?`)')
    
    for match in pattern.finditer(text):
        # Add plain text before match
        if match.start() > pos:
            plain = text[pos:match.start()]
            if plain:
                elements.append({"type": "text", "text": plain})
        
        # Add styled text
        matched = match.group(0)
        if matched.startswith('*') and matched.endswith('*'):
            elements.append({"type": "text", "text": matched[1:-1], "style": {"bold": True}})
        elif matched.startswith('_') and matched.endswith('_'):
            elements.append({"type": "text", "text": matched[1:-1], "style": {"italic": True}})
        elif matched.startswith('~') and matched.endswith('~'):
            elements.append({"type": "text", "text": matched[1:-1], "style": {"strike": True}})
        elif matched.startswith('`') and matched.endswith('`'):
            elements.append({"type": "text", "text": matched[1:-1], "style": {"code": True}})
        
        pos = match.end()
    
    # Add remaining plain text
    if pos < len(text):
        remaining = text[pos:]
        if remaining:
            elements.append({"type": "text", "text": remaining})
    
    return elements if elements else [{"type": "text", "text": text}]


def _build_slack_blocks(text: str, max_chars: int = 2900) -> list[dict[str, Any]]:
    """Build Slack blocks using rich_text for proper list rendering."""
    formatted = _markdown_to_mrkdwn(text)
    blocks = []
    
    # Split into paragraphs
    paragraphs = formatted.split("\n\n")
    
    for para in paragraphs:
        lines = para.split("\n")
        
        # Check if this is a list block (lines starting with •)
        if any(line.lstrip().startswith("• ") for line in lines):
            # Group consecutive lines by indent level
            list_groups = []  # [{indent: 0, items: [...]}, {indent: 1, items: [...]}, ...]
            
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith("• "):
                    indent_level = (len(line) - len(stripped)) // 2  # 2 spaces per level
                    text_content = stripped[2:]  # Remove "• "
                    
                    # If indent changed, start new group
                    if not list_groups or list_groups[-1]["indent"] != indent_level:
                        list_groups.append({"indent": indent_level, "items": []})
                    
                    # Parse inline formatting in list item text
                    text_elements = _parse_rich_text_elements(text_content)
                    
                    # Add item to current group
                    list_groups[-1]["items"].append({
                        "type": "rich_text_section",
                        "elements": text_elements
                    })
            
            # Build single rich_text block with all list groups
            if list_groups:
                rich_text_lists = []
                for group in list_groups:
                    rich_text_lists.append({
                        "type": "rich_text_list",
                        "style": "bullet",
                        "indent": group["indent"],
                        "elements": group["items"]
                    })
                
                blocks.append({
                    "type": "rich_text",
                    "elements": rich_text_lists
                })
        else:
            # Non-list paragraph: use section block with mrkdwn
            if para.strip():
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": para.strip()},
                })
    
    return blocks


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

def _upload_pending_files(client, channel: str, thread_ts: str | None, session_id: str):
    """Upload any files the agent produced (CSV, Excel, charts) to Slack."""
    files = get_pending_files_for_session(session_id)
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

    clear_pending_files_for_session(session_id)


def _handle(text: str, say, client, thread_ts: str | None = None, user_id: str | None = None, channel: str | None = None):
    """Run the agent and post the reply."""
    if not text:
        say("Hey! Ask me a data question :wave:", thread_ts=thread_ts)
        return

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
    langfuse_trace_id: str | None = None
    langfuse_sync: bool = APP_SETTINGS.observability.langfuse_sync
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(
                agent.run_sync,
                text,
                message_history=history or None,
                deps=core_agent,  # Reuse the shared DataAgent
                usage_limits=UsageLimits(request_limit=12, tool_calls_limit=20),
                metadata={
                    "interface": "slack",
                    "user_id": user_id,
                    "thread_ts": thread_ts,
                    "channel": channel,
                },
            )
            try:
                result = future.result(timeout=QUERY_TIMEOUT)
            except FuturesTimeoutError:
                reply = (
                    "That query took too long. Try narrowing the scope or breaking it "
                    "into smaller questions."
                )
            else:
                reply = result.output or "I couldn't generate a response — try rephrasing?"
                tool_calls = _extract_tool_calls(result.all_messages())
                # Create LangFuse trace when enabled (auto-detected from env vars)
                # Check if Langfuse is configured (via env vars)
                if os.getenv("LANGFUSE_PUBLIC_KEY"):
                    from falk.observability import trace_agent_run

                    trace = trace_agent_run(text, result, user_id=user_id, sync=langfuse_sync)
                    if trace and hasattr(trace, "id"):
                        langfuse_trace_id = trace.id

                # Persist conversation for follow-ups
                if thread_ts:
                    _store_history(thread_ts, result.all_messages())
    except FuturesTimeoutError:
        reply = (
            "That query took too long. Try narrowing the scope or breaking it "
            "into smaller questions."
        )
    except UsageLimitExceeded:
        reply = (
            "That query used too many steps. Try a simpler or more focused question."
        )
    except Exception:
        logger.exception("Agent error")
        reply = "Something went wrong — please try again in a moment."

    # Format reply and update the Thinking message (or post new if update fails)
    reply_formatted = _markdown_to_mrkdwn(reply)
    reply_formatted = _strip_file_paths(reply_formatted)
    
    # Tag user in public channels/mentions (not in DMs or slash commands without thread)
    # Only tag if we're in a thread (thread_ts) which indicates a channel conversation
    if user_id and channel and thread_ts:
        reply_formatted = f"<@{user_id}> {reply_formatted}"
    
    blocks = _build_slack_blocks(reply_formatted)

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
            _upload_pending_files(client, channel, thread_ts, session_id)

        if message_ts and channel:
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

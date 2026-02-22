"""Slack text formatting helpers.

Keeps Markdown -> Slack mrkdwn conversion and block construction isolated from
Slack transport code so behavior is easier to test.
"""
from __future__ import annotations

import html
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BOLD_PLACEHOLDER = "\x00BOLD{}\x00"


def _markdown_to_mrkdwn(text: str) -> str:
    """Convert Markdown-like text to Slack mrkdwn."""
    if not text:
        return ""

    try:
        text = html.unescape(text.strip())
        in_code_block = False
        out_lines: list[str] = []

        for raw_line in text.split("\n"):
            line = raw_line
            if re.match(r"^```\s*\w*\s*$", line.strip()) or line.strip() == "```":
                in_code_block = not in_code_block
                out_lines.append(line)
                continue

            if in_code_block:
                out_lines.append(line)
                continue

            # Headings become Slack bold.
            line = re.sub(r"^#{1,6}\s+(.+?)\s*$", r"**\1**", line)

            bold_segments: list[str] = []

            def _stash_bold(match: re.Match[str]) -> str:
                bold_segments.append(match.group(1))
                return _BOLD_PLACEHOLDER.format(len(bold_segments) - 1)

            # Protect bold while we convert single-star italic.
            line = re.sub(r"(?<!\*)\*\*([^\n]+?)\*\*(?!\*)", _stash_bold, line)
            line = re.sub(r"__([^\n]+?)__", _stash_bold, line)

            # Markdown bullets -> Slack bullet character.
            line = re.sub(r"^(\s*)([-*\u2022])\s+(.+)$", r"\1• \3", line)
            line = re.sub(r"^(\s*)\d+\.\s+(.+)$", r"\1• \2", line)

            # Markdown italic -> Slack italic.
            line = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"_\1_", line)

            # Restore protected bold segments as Slack bold.
            for idx, segment in enumerate(bold_segments):
                line = line.replace(_BOLD_PLACEHOLDER.format(idx), f"*{segment}*")

            out_lines.append(line)

        result = "\n".join(out_lines)
        result = re.sub(r"\[(.+?)\]\((.+?)\)", r"<\2|\1>", result)
        result = re.sub(r"~~(.+?)~~", r"~\1~", result)
        result = re.sub(r"\*\*\s*$", "", result)
        return result.strip()
    except Exception:
        logger.exception("Markdown conversion error")
        return text


def _strip_file_paths(text: str) -> str:
    """Remove full file paths from messages — files are uploaded to Slack."""

    def _replace_link(match: re.Match[str]) -> str:
        _link_text, url = match.group(1), match.group(2)
        if any(
            url.rstrip().lower().endswith(ext)
            for ext in (".csv", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".gif")
        ):
            return "in the attachment above"
        return match.group(0)

    text = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", _replace_link, text)
    text = re.sub(
        r"[A-Za-z]:\\[^\s]+\.(csv|xlsx|xls|png|jpg|jpeg|gif)\b",
        lambda m: Path(m.group(0)).name,
        text,
    )
    return text


def _parse_rich_text_elements(text: str) -> list[dict[str, Any]]:
    """Parse mrkdwn inline styles into rich_text elements."""
    elements: list[dict[str, Any]] = []
    pos = 0
    markers = {"*": "bold", "_": "italic", "~": "strike", "`": "code"}

    while pos < len(text):
        char = text[pos]
        style_name = markers.get(char)
        if not style_name:
            next_marker_positions = [text.find(m, pos) for m in markers]
            valid_positions = [p for p in next_marker_positions if p != -1]
            end = min(valid_positions) if valid_positions else len(text)
            plain = text[pos:end]
            if plain:
                elements.append({"type": "text", "text": plain})
            pos = end
            continue

        close = text.find(char, pos + 1)
        if close == -1 or "\n" in text[pos + 1 : close]:
            elements.append({"type": "text", "text": char})
            pos += 1
            continue

        content = text[pos + 1 : close]
        if not content:
            elements.append({"type": "text", "text": char * 2})
            pos = close + 1
            continue

        elements.append({"type": "text", "text": content, "style": {style_name: True}})
        pos = close + 1

    return elements if elements else [{"type": "text", "text": text}]


def _build_list_block(list_lines: list[str]) -> dict[str, Any] | None:
    """Build one rich_text list block from consecutive list lines."""
    if not list_lines:
        return None

    groups: list[dict[str, Any]] = []
    for line in list_lines:
        stripped = line.lstrip()
        if not stripped.startswith("• "):
            continue
        indent_level = (len(line) - len(stripped)) // 2
        text_content = stripped[2:]
        section = {
            "type": "rich_text_section",
            "elements": _parse_rich_text_elements(text_content),
        }
        if not groups or groups[-1]["indent"] != indent_level:
            groups.append({"indent": indent_level, "items": []})
        groups[-1]["items"].append(section)

    if not groups:
        return None

    return {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_list",
                "style": "bullet",
                "indent": group["indent"],
                "elements": group["items"],
            }
            for group in groups
        ],
    }


def _build_slack_blocks(text: str, max_chars: int = 2900) -> list[dict[str, Any]]:
    """Build Slack blocks using rich_text for list rendering."""
    formatted = _markdown_to_mrkdwn(text)
    blocks: list[dict[str, Any]] = []
    if not formatted:
        return blocks

    paragraphs = formatted.split("\n\n")
    for para in paragraphs:
        lines = para.split("\n")
        text_lines: list[str] = []
        list_lines: list[str] = []

        def _flush_text() -> None:
            if not text_lines:
                return
            content = "\n".join(text_lines).strip()
            if content:
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": content[:max_chars]}})
            text_lines.clear()

        def _flush_list() -> None:
            if not list_lines:
                return
            list_block = _build_list_block(list_lines)
            if list_block:
                blocks.append(list_block)
            list_lines.clear()

        for line in lines:
            if line.lstrip().startswith("• "):
                _flush_text()
                list_lines.append(line)
            else:
                _flush_list()
                text_lines.append(line)

        _flush_list()
        _flush_text()

    return blocks


def format_reply_for_slack(
    reply: str,
    user_id: str | None = None,
    channel: str | None = None,
    thread_ts: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Normalize agent output for Slack message text + blocks."""
    reply_formatted = _markdown_to_mrkdwn(reply)
    reply_formatted = _strip_file_paths(reply_formatted)
    if user_id and channel and thread_ts:
        reply_formatted = f"<@{user_id}>\n{reply_formatted}"
    return reply_formatted, _build_slack_blocks(reply_formatted)

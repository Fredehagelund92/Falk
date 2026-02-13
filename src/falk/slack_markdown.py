"""Slack mrkdwn converter — Markdown to Slack format."""
from __future__ import annotations

import html
import logging
import re

logger = logging.getLogger(__name__)


def markdown_to_mrkdwn(text: str) -> str:
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
        logger.error("Markdown conversion error: %s", e)
        return text

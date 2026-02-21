from __future__ import annotations

from falk.slack_formatting import (
    _build_slack_blocks,
    _markdown_to_mrkdwn,
    format_reply_for_slack,
)


def test_markdown_to_mrkdwn_preserves_bold_and_italic_roles():
    text = "Revenue is **up** and *steady*."

    converted = _markdown_to_mrkdwn(text)

    assert converted == "Revenue is *up* and _steady_."


def test_markdown_to_mrkdwn_converts_nested_lists():
    text = "- Revenue\n  - EU\n1. Orders"

    converted = _markdown_to_mrkdwn(text)

    assert converted.splitlines() == ["• Revenue", "  • EU", "• Orders"]


def test_build_slack_blocks_handles_mixed_text_and_lists():
    text = "Summary line\n- **Revenue** up\n  - *EU* strong\nNext step line"

    blocks = _build_slack_blocks(text)

    assert [block["type"] for block in blocks] == ["section", "rich_text", "section"]
    assert blocks[0]["text"]["text"] == "Summary line"
    assert blocks[2]["text"]["text"] == "Next step line"

    rich_lists = blocks[1]["elements"]
    assert [entry["indent"] for entry in rich_lists] == [0, 1]
    top_item_elements = rich_lists[0]["elements"][0]["elements"]
    nested_item_elements = rich_lists[1]["elements"][0]["elements"]
    assert top_item_elements[0]["style"] == {"bold": True}
    assert nested_item_elements[0]["style"] == {"italic": True}


def test_format_reply_for_slack_mentions_user_on_newline_in_threads():
    text, _blocks = format_reply_for_slack(
        "All good",
        user_id="U123",
        channel="C123",
        thread_ts="1700000.0001",
    )

    assert text == "<@U123>\nAll good"


def test_format_reply_for_slack_no_mention_without_thread():
    text, _blocks = format_reply_for_slack(
        "All good",
        user_id="U123",
        channel="C123",
        thread_ts=None,
    )

    assert text == "All good"

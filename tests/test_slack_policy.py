from __future__ import annotations

from falk.settings import SlackPolicyConfig
from falk.slack.policy import can_deliver_exports, is_dm_channel


def test_is_dm_channel_detects_dm_prefix():
    assert is_dm_channel("D12345") is True
    assert is_dm_channel("C12345") is False
    assert is_dm_channel(None) is False


def test_can_deliver_exports_allows_dm_and_allowlist():
    policy = SlackPolicyConfig(
        exports_dm_only=True,
        export_channel_allowlist=["C_ALLOWED"],
        export_block_message="blocked",
    )
    assert can_deliver_exports("D_DM", policy) is True
    assert can_deliver_exports("C_ALLOWED", policy) is True
    assert can_deliver_exports("C_OTHER", policy) is False

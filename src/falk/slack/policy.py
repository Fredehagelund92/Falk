"""Slack export-delivery policy helpers."""

from __future__ import annotations

from falk.settings import SlackPolicyConfig


def is_dm_channel(channel: str | None) -> bool:
    """Return True for Slack DM channels (IDs prefixed with D)."""
    return bool(channel and channel.startswith("D"))


def can_deliver_exports(channel: str | None, policy: SlackPolicyConfig) -> bool:
    """Return True if export files are allowed in the current channel."""
    if is_dm_channel(channel):
        return True
    if channel and channel in set(policy.export_channel_allowlist):
        return True
    return not policy.exports_dm_only

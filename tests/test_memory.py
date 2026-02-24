"""Tests for long-term memory abstraction."""

from __future__ import annotations

from falk.llm.memory import (
    NoOpMemoryService,
    get_memory_service,
    reset_memory_service,
    retain_interaction_sync,
)


def test_noop_memory_does_nothing():
    service = NoOpMemoryService()
    # Should not raise
    import asyncio

    asyncio.run(service.retain("s1", "u1", "q", "r"))
    result = asyncio.run(service.recall("s1", "u1", "q"))
    assert result == ""
    assert asyncio.run(service.reflect("s1", "u1", "q")) is None


def test_get_memory_service_returns_noop_when_disabled():
    reset_memory_service()
    service = get_memory_service(enabled=False)
    assert isinstance(service, NoOpMemoryService)


def test_retain_interaction_sync_noop_when_disabled():
    # Should not raise
    retain_interaction_sync(
        session_id="s1",
        user_id="u1",
        query="q",
        response="r",
        enabled=False,
    )

"""Optional long-term memory for agent context.

Provides retain/recall/reflect operations. Default implementation is no-op.
Enable via memory.enabled in falk_project.yaml and set memory.provider for a backend.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class MemoryService(Protocol):
    """Interface for long-term memory operations."""

    async def retain(
        self,
        session_id: str,
        user_id: str | None,
        query: str,
        response: str,
        tool_calls: list[dict[str, Any]] | None = None,
        **attrs: Any,
    ) -> None:
        """Store an interaction for future recall. No-op if not implemented."""
        ...

    async def recall(
        self,
        session_id: str,
        user_id: str | None,
        query: str,
        limit: int = 3,
    ) -> str:
        """Recall relevant context for a query. Returns empty string if none."""
        ...

    async def reflect(
        self,
        session_id: str,
        user_id: str | None,
        question: str,
        context: str | None = None,
    ) -> str | None:
        """Reflect on a question with optional context. Returns None if not implemented."""
        ...


class NoOpMemoryService:
    """Default memory service that does nothing."""

    async def retain(
        self,
        session_id: str,
        user_id: str | None,
        query: str,
        response: str,
        tool_calls: list[dict[str, Any]] | None = None,
        **attrs: Any,
    ) -> None:
        pass

    async def recall(
        self,
        session_id: str,
        user_id: str | None,
        query: str,
        limit: int = 3,
    ) -> str:
        return ""

    async def reflect(
        self,
        session_id: str,
        user_id: str | None,
        question: str,
        context: str | None = None,
    ) -> str | None:
        return None


_memory_service: MemoryService | None = None


def get_memory_service(enabled: bool = False, provider: str | None = None) -> MemoryService:
    """Get the memory service. Returns no-op if disabled or provider not configured."""
    global _memory_service
    if _memory_service is not None:
        return _memory_service

    if not enabled or not provider:
        _memory_service = NoOpMemoryService()
        return _memory_service

    if provider == "hindsight":
        try:
            from falk.backends.memory.hindsight import HindsightMemoryService

            _memory_service = HindsightMemoryService()
            logger.info("Hindsight memory service initialized")
            return _memory_service
        except ImportError as e:
            logger.warning("Hindsight memory requested but not available: %s", e)
            _memory_service = NoOpMemoryService()
            return _memory_service

    _memory_service = NoOpMemoryService()
    return _memory_service


def reset_memory_service() -> None:
    """Reset the memory service (for testing)."""
    global _memory_service
    _memory_service = None


def retain_interaction_sync(
    session_id: str,
    user_id: str | None,
    query: str,
    response: str,
    tool_calls: list[dict[str, Any]] | None = None,
    enabled: bool = False,
    provider: str | None = None,
) -> None:
    """Best-effort retain. Runs async retain in a thread; failures are logged, not raised."""
    if not enabled or not provider:
        return
    try:
        import asyncio

        service = get_memory_service(enabled=enabled, provider=provider)
        asyncio.run(
            service.retain(
                session_id=session_id,
                user_id=user_id,
                query=query,
                response=(response or "")[:500],
                tool_calls=tool_calls,
            )
        )
    except Exception as e:
        logger.debug("Memory retain failed (non-fatal): %s", e)

"""Hindsight memory backend (optional).

Requires the hindsight package. Configure with:
  memory:
    enabled: true
    provider: hindsight
  HINDSIGHT_API_KEY=...  # in .env

See https://hindsight.vectorize.io/ for API docs.
"""

from __future__ import annotations

from typing import Any


class HindsightMemoryService:
    """Hindsight-based long-term memory. Requires hindsight package."""

    def __init__(self) -> None:
        try:
            import hindsight  # noqa: F401
        except ImportError:
            raise ImportError(
                "Hindsight memory requires the hindsight package. "
                "Install with: pip install hindsight-api"
            ) from None

    async def retain(
        self,
        session_id: str,
        user_id: str | None,
        query: str,
        response: str,
        tool_calls: list[dict[str, Any]] | None = None,
        **attrs: Any,
    ) -> None:
        """Store interaction in Hindsight bank. Stub for future implementation."""
        pass

    async def recall(
        self,
        session_id: str,
        user_id: str | None,
        query: str,
        limit: int = 3,
    ) -> str:
        """Recall from Hindsight. Stub for future implementation."""
        return ""

    async def reflect(
        self,
        session_id: str,
        user_id: str | None,
        question: str,
        context: str | None = None,
    ) -> str | None:
        """Reflect via Hindsight. Stub for future implementation."""
        return None

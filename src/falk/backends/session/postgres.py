"""PostgreSQL-backed session store backend."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as SASession

logger = logging.getLogger(__name__)


class PostgresSessionStore:
    """PostgreSQL-backed session store.

    Suitable for production. Falk auto-creates schema and table on first use.
    """

    def __init__(self, url: str, schema: str = "falk_session", ttl: int = 3600):
        if not url or not url.strip():
            raise ValueError(
                "Postgres session store requires POSTGRES_URL. "
                "Set it in .env or session.postgres_url in falk_project.yaml."
            )
        self._url = url.strip()
        self._schema = schema or "falk_session"
        self._ttl = ttl
        self._engine = create_engine(self._url)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create schema and table if they do not exist."""
        create_schema = text(f"CREATE SCHEMA IF NOT EXISTS {self._schema}")
        create_table = text(f"""
            CREATE TABLE IF NOT EXISTS {self._schema}.session_state (
                session_id TEXT PRIMARY KEY,
                state_json JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            )
        """)
        idx_name = f"ix_{self._schema.replace('.', '_')}_expires"
        create_index = text(
            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {self._schema}.session_state (expires_at)"
        )
        with self._engine.connect() as conn:
            conn.execute(create_schema)
            conn.execute(create_table)
            conn.execute(create_index)
            conn.commit()

    def get(self, session_id: str) -> dict[str, Any] | None:
        now = datetime.now(UTC)
        with SASession(self._engine) as session:
            result = session.execute(
                text(
                    f"SELECT state_json, expires_at FROM {self._schema}.session_state "
                    "WHERE session_id = :sid"
                ),
                {"sid": session_id},
            )
            row = result.fetchone()
            if not row:
                return None
            state_json, expires_at = row
            if expires_at and expires_at <= now:
                session.execute(
                    text(f"DELETE FROM {self._schema}.session_state WHERE session_id = :sid"),
                    {"sid": session_id},
                )
                session.commit()
                return None
            return dict(state_json) if state_json else None

    def set(self, session_id: str, state: dict[str, Any]) -> None:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._ttl)
        # Ensure JSON-serializable; psycopg accepts dict for JSONB
        state_copy = json.loads(json.dumps(state))
        with SASession(self._engine) as session:
            session.execute(
                text(f"""
                    INSERT INTO {self._schema}.session_state
                    (session_id, state_json, updated_at, expires_at)
                    VALUES (:sid, :state_json, :updated_at, :expires_at)
                    ON CONFLICT (session_id) DO UPDATE SET
                        state_json = :state_json,
                        updated_at = :updated_at,
                        expires_at = :expires_at
                """),
                {
                    "sid": session_id,
                    "state_json": state_copy,
                    "updated_at": now,
                    "expires_at": expires_at,
                },
            )
            session.commit()

    def clear(self, session_id: str) -> None:
        with SASession(self._engine) as session:
            session.execute(
                text(f"DELETE FROM {self._schema}.session_state WHERE session_id = :sid"),
                {"sid": session_id},
            )
            session.commit()

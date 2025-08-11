"""
In-memory SQLite persistence adapter for tests and simple runs.

Implements IPersistencePort without importing infrastructure, keeping
hexagonal boundaries intact. Uses one SQLite :memory: database per story_id.
"""

from __future__ import annotations

import sqlite3
from threading import RLock
from typing import Any, Optional

from .persistence_port import IPersistencePort


class InMemorySqlitePersistence(IPersistencePort):
    """Simple in-memory SQLite implementation of IPersistencePort."""

    def __init__(self) -> None:
        self._connections: dict[str, sqlite3.Connection] = {}
        self._lock = RLock()

    def _get_conn(self, story_id: str) -> sqlite3.Connection:
        with self._lock:
            conn = self._connections.get(story_id)
            if conn is None:
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                self._connections[story_id] = conn
            return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scenes (
                scene_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                input TEXT NOT NULL,
                output TEXT NOT NULL,
                memory_snapshot TEXT,
                flags TEXT,
                canon_refs TEXT,
                analysis TEXT,
                scene_label TEXT,
                structured_tags TEXT,
                story_id TEXT NOT NULL
            )
            """
        )
        conn.commit()

    # IPersistencePort implementation
    def execute_query(
        self, story_id: str, query: str, params: Optional[list[Any] | tuple[Any, ...]] = None
    ) -> list[dict[str, Any]]:
        conn = self._get_conn(story_id)
        self._ensure_schema(conn)
        cur = conn.execute(query, params or [])
        rows = cur.fetchall()
        # Convert sqlite3.Row to dict
        return [dict(r) for r in rows]

    def execute_update(
        self, story_id: str, query: str, params: Optional[list[Any] | tuple[Any, ...]] = None
    ) -> bool:
        conn = self._get_conn(story_id)
        self._ensure_schema(conn)
        cur = conn.execute(query, params or [])
        conn.commit()
        # SQLite returns -1 for rowcount when not applicable; treat as success
        return cur.rowcount is None or cur.rowcount >= -1

    def init_database(self, story_id: str) -> bool:
        conn = self._get_conn(story_id)
        self._ensure_schema(conn)
        return True

    def backup_database(self, story_id: str, backup_name: str) -> bool:
        # No-op for in-memory DB
        return True

    def restore_database(self, story_id: str, backup_name: str) -> bool:
        # No-op for in-memory DB
        return True

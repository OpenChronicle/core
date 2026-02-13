from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from openchronicle.core.domain.models.project import Agent, Project
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


def _new_store(tmp_path: Path) -> SqliteStore:
    db_path = tmp_path / "test.db"
    store = SqliteStore(str(db_path))
    store.init_schema()
    return store


def test_sqlite_pragmas_enabled(tmp_path: Path) -> None:
    """Ensure SQLite connections enable durability and FK enforcement."""

    store = _new_store(tmp_path)
    cur = store._conn.cursor()

    foreign_keys = cur.execute("PRAGMA foreign_keys").fetchone()[0]
    journal_mode = str(cur.execute("PRAGMA journal_mode").fetchone()[0]).lower()
    synchronous = str(cur.execute("PRAGMA synchronous").fetchone()[0]).lower()
    busy_timeout = cur.execute("PRAGMA busy_timeout").fetchone()[0]

    assert foreign_keys == 1
    assert journal_mode == "wal"
    assert synchronous in {"1", "normal"}
    assert busy_timeout == 5000


def test_transaction_rolls_back_on_exception(tmp_path: Path) -> None:
    """Transaction context rolls back when an exception is raised."""

    store = _new_store(tmp_path)
    project = Project(name="Tx Rollback")

    with pytest.raises(RuntimeError, match="boom"):
        with store.transaction():
            store.add_project(project)
            raise RuntimeError("boom")

    assert store.get_project(project.id) is None


def test_nested_transaction_commits(tmp_path: Path) -> None:
    """Nested transactions (savepoints) commit together on success."""

    store = _new_store(tmp_path)
    project = Project(name="Tx Nested")
    agent = Agent(project_id=project.id, name="Worker")

    with store.transaction():
        store.add_project(project)
        with store.transaction():
            store.add_agent(agent)

    persisted_project = store.get_project(project.id)
    assert persisted_project is not None

    agents = store.list_agents(project.id)
    assert len(agents) == 1
    assert agents[0].id == agent.id


def test_begin_immediate_retries_on_lock_contention(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_begin_immediate_with_retry retries on 'database is locked' then succeeds."""
    import sqlite3
    import time
    from unittest.mock import MagicMock

    store = _new_store(tmp_path)
    real_conn = store._conn

    call_count = 0

    def _flaky_execute(sql: str, *args: Any) -> Any:
        nonlocal call_count
        if sql == "BEGIN IMMEDIATE":
            call_count += 1
            if call_count <= 2:
                raise sqlite3.OperationalError("database is locked")
        return real_conn.execute(sql, *args)

    # Wrap _conn so .execute is patchable (C-level attr is read-only).
    wrapper = MagicMock(wraps=real_conn)
    wrapper.execute = _flaky_execute
    store._conn = wrapper

    monkeypatch.setattr(time, "sleep", lambda _: None)

    project = Project(name="Retry Test")
    with store.transaction():
        store.add_project(project)

    # Restore real connection for the read.
    store._conn = real_conn
    assert store.get_project(project.id) is not None
    # 2 failures + 1 success = 3 calls to BEGIN IMMEDIATE.
    assert call_count == 3


def test_begin_immediate_raises_after_max_retries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_begin_immediate_with_retry raises after exhausting retries."""
    import sqlite3
    import time
    from unittest.mock import MagicMock

    store = _new_store(tmp_path)
    real_conn = store._conn

    def _always_locked(sql: str, *args: Any) -> Any:
        if sql == "BEGIN IMMEDIATE":
            raise sqlite3.OperationalError("database is locked")
        return real_conn.execute(sql, *args)

    wrapper = MagicMock(wraps=real_conn)
    wrapper.execute = _always_locked
    store._conn = wrapper

    monkeypatch.setattr(time, "sleep", lambda _: None)

    with pytest.raises(sqlite3.OperationalError, match="locked"):
        with store.transaction():
            pass

    store._conn = real_conn  # pragma: no cover


def test_begin_immediate_does_not_retry_non_lock_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-lock OperationalErrors propagate immediately without retry."""
    import sqlite3
    import time
    from unittest.mock import MagicMock

    store = _new_store(tmp_path)
    real_conn = store._conn

    call_count = 0

    def _other_error(sql: str, *args: Any) -> Any:
        nonlocal call_count
        if sql == "BEGIN IMMEDIATE":
            call_count += 1
            raise sqlite3.OperationalError("disk I/O error")
        return real_conn.execute(sql, *args)

    wrapper = MagicMock(wraps=real_conn)
    wrapper.execute = _other_error
    store._conn = wrapper

    monkeypatch.setattr(time, "sleep", lambda _: None)

    with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
        with store.transaction():
            pass

    store._conn = real_conn
    assert call_count == 1, "Non-lock errors should not trigger retry"

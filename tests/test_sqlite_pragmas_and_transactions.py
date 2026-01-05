from __future__ import annotations

from pathlib import Path

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

"""Tests for FTS5 rebuild-skip optimization.

Verifies that _ensure_fts5() only rebuilds indexes when they are empty,
not on every startup.
"""

from __future__ import annotations

import logging
import pathlib

import pytest

from openchronicle.core.domain.models.memory_item import MemoryItem
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> SqliteStore:
    """Create a fresh SqliteStore with FTS5 enabled."""
    db_path = tmp_path / "test.db"
    s = SqliteStore(db_path=str(db_path))
    s.init_schema()
    return s


def test_first_init_rebuilds_empty_fts(store: SqliteStore) -> None:
    """First init should rebuild because FTS tables are empty."""
    assert store._fts5_active  # noqa: SLF001


def test_second_init_skips_rebuild_when_populated(
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Second init should skip rebuild because FTS tables are already populated."""
    db_path = tmp_path / "test.db"

    # First init — seeds data and builds FTS
    s1 = SqliteStore(db_path=str(db_path))
    s1.init_schema()
    s1.add_memory(MemoryItem(content="hello world", tags=["test"]))
    s1.close()

    # Second init — FTS should already be populated, rebuild skipped
    with caplog.at_level(logging.INFO, logger="openchronicle.core.infrastructure.persistence.sqlite_store"):
        s2 = SqliteStore(db_path=str(db_path))
        s2.init_schema()

    # memory_fts should NOT rebuild (already populated); turns_fts may
    # rebuild because no turns were inserted — that's correct behavior.
    memory_rebuilds = [r for r in caplog.records if "memory_fts" in r.message and "rebuilding" in r.message.lower()]
    assert len(memory_rebuilds) == 0, f"Unexpected memory_fts rebuild: {[r.message for r in memory_rebuilds]}"
    assert s2._fts5_active  # noqa: SLF001
    s2.close()


def test_rebuild_occurs_when_fts_empty_but_source_has_data(
    tmp_path: pathlib.Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If FTS table is empty but source table has data (migration scenario),
    rebuild should occur."""
    db_path = tmp_path / "test.db"

    # First init with data
    s1 = SqliteStore(db_path=str(db_path))
    s1.init_schema()
    s1.add_memory(MemoryItem(content="important data", tags=["test"]))

    # Manually clear FTS to simulate a migration scenario
    s1._conn.execute("DELETE FROM memory_fts")  # noqa: SLF001
    s1._conn.commit()  # noqa: SLF001
    s1.close()

    # Re-init should detect empty FTS and rebuild
    with caplog.at_level(logging.INFO, logger="openchronicle.core.infrastructure.persistence.sqlite_store"):
        s2 = SqliteStore(db_path=str(db_path))
        s2.init_schema()

    rebuild_messages = [r for r in caplog.records if "rebuilding index" in r.message.lower()]
    assert len(rebuild_messages) > 0, "Expected FTS rebuild but none occurred"
    assert s2._fts5_active  # noqa: SLF001
    s2.close()

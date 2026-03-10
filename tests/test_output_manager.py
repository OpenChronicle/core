"""Tests for OutputManager service."""

from __future__ import annotations

import json
import pathlib
import time

import pytest

from openchronicle.core.application.services.output_manager import OutputManager
from openchronicle.core.domain.exceptions import ValidationError


@pytest.fixture()
def manager(tmp_path: pathlib.Path) -> OutputManager:
    return OutputManager(base_dir=str(tmp_path))


# --- save_report ---


def test_save_report_creates_timestamped_json(manager: OutputManager) -> None:
    path = manager.save_report("scan", {"status": "ok"})
    assert path.exists()
    assert path.suffix == ".json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "ok"


def test_save_report_creates_latest_pointer(manager: OutputManager) -> None:
    manager.save_report("scan", {"run": 1})
    latest = manager.latest_output("scan")
    assert latest is not None
    data = json.loads(latest.read_text(encoding="utf-8"))
    assert data["run"] == 1


def test_save_report_creates_type_dir(manager: OutputManager) -> None:
    manager.save_report("new-type", {"a": 1})
    type_dir = pathlib.Path(manager.base_dir) / "new-type"
    assert type_dir.is_dir()


def test_save_report_rejects_path_traversal(manager: OutputManager) -> None:
    with pytest.raises(ValidationError):
        manager.save_report("../escape", {"bad": True})


def test_save_report_rejects_empty_type(manager: OutputManager) -> None:
    with pytest.raises(ValidationError):
        manager.save_report("", {"bad": True})


# --- list_outputs ---


def test_list_outputs_newest_first(manager: OutputManager) -> None:
    manager.save_report("scan", {"run": 1})
    time.sleep(1.1)  # ensure different timestamp
    manager.save_report("scan", {"run": 2})
    files = manager.list_outputs("scan")
    assert len(files) == 2
    # Newest first (higher timestamp sorts first in reverse)
    assert files[0].name > files[1].name


def test_list_outputs_excludes_latest(manager: OutputManager) -> None:
    manager.save_report("scan", {"run": 1})
    files = manager.list_outputs("scan")
    names = [f.name for f in files]
    assert "latest.json" not in names


def test_list_outputs_empty_for_unknown_type(manager: OutputManager) -> None:
    files = manager.list_outputs("nonexistent")
    assert files == []


# --- latest_output ---


def test_latest_output_returns_path_when_exists(manager: OutputManager) -> None:
    manager.save_report("scan", {"data": True})
    path = manager.latest_output("scan")
    assert path is not None
    assert path.name == "latest.json"


def test_latest_output_returns_none_when_missing(manager: OutputManager) -> None:
    assert manager.latest_output("nonexistent") is None


# --- cleanup ---


def test_cleanup_deletes_old_preserves_recent(manager: OutputManager, tmp_path: pathlib.Path) -> None:
    # Create a fake old file by writing directly
    type_dir = tmp_path / "scan"
    type_dir.mkdir()
    old_file = type_dir / "20200101_000000.json"
    old_file.write_text("{}", encoding="utf-8")
    # Backdate the file
    import os

    old_time = time.time() - 86400 * 100  # 100 days ago
    os.utime(old_file, (old_time, old_time))

    # Save a recent file
    manager.save_report("scan", {"recent": True})

    deleted = manager.cleanup(max_age_days=30)
    assert deleted == 1
    assert not old_file.exists()
    # Recent file + latest should still exist
    remaining = list(type_dir.glob("*.json"))
    assert len(remaining) == 2  # recent + latest


def test_cleanup_preserves_latest_pointer(manager: OutputManager, tmp_path: pathlib.Path) -> None:
    type_dir = tmp_path / "scan"
    type_dir.mkdir()
    latest = type_dir / "latest.json"
    latest.write_text("{}", encoding="utf-8")
    # Backdate latest
    import os

    old_time = time.time() - 86400 * 100
    os.utime(latest, (old_time, old_time))

    deleted = manager.cleanup(max_age_days=1)
    assert deleted == 0  # latest.json is always preserved
    assert latest.exists()


def test_cleanup_rejects_zero_days(manager: OutputManager) -> None:
    with pytest.raises(ValidationError):
        manager.cleanup(max_age_days=0)


def test_cleanup_handles_missing_dir(tmp_path: pathlib.Path) -> None:
    mgr = OutputManager(base_dir=str(tmp_path / "nonexistent"))
    deleted = mgr.cleanup(max_age_days=7)
    assert deleted == 0

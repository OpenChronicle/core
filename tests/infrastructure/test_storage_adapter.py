"""Tests for StorageAdapter basic file operations.

Verifies save/load round trips for text and binary content and list_files relative path behavior.
"""
from pathlib import Path

from openchronicle.infrastructure.persistence_adapters.storage_adapter import StorageAdapter


def test_save_and_load_text(tmp_path: Path):
    adapter = StorageAdapter(base_storage_path=str(tmp_path / "storage"))
    story_id = "story1"
    file_rel = "scenes/intro.txt"
    content = "Hello Chronicle"
    assert adapter.save_file(story_id, file_rel, content) is True
    loaded = adapter.load_file(story_id, file_rel)
    assert loaded == content


def test_save_and_load_binary(tmp_path: Path):
    adapter = StorageAdapter(base_storage_path=str(tmp_path / "storage"))
    story_id = "story2"
    file_rel = "assets/image.bin"
    data = b"\x00\x01binarydata"
    assert adapter.save_file(story_id, file_rel, data) is True
    loaded = adapter.load_file(story_id, file_rel)
    assert isinstance(loaded, bytes)
    assert loaded == data


def test_list_files_returns_relative_paths(tmp_path: Path):
    adapter = StorageAdapter(base_storage_path=str(tmp_path / "storage"))
    story_id = "story3"
    adapter.save_file(story_id, "a/b/c.txt", "x")
    adapter.save_file(story_id, "a/d/e.txt", "y")
    files = adapter.list_files(story_id)
    # Ensure relative paths without story prefix
    assert "a/b/c.txt" in files
    assert "a/d/e.txt" in files
    # Ensure no absolute path leaks
    assert all(not f.startswith(str(tmp_path)) for f in files)

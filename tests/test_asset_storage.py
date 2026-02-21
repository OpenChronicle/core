"""Tests for AssetFileStorage — filesystem operations and hashing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openchronicle.core.application.services.asset_storage import AssetFileStorage
from openchronicle.core.domain.models.asset import Asset


def _make_asset(**overrides: Any) -> Asset:
    defaults: dict[str, Any] = {
        "id": "asset-1",
        "project_id": "proj-1",
        "filename": "photo.png",
        "mime_type": "image/png",
    }
    defaults.update(overrides)
    return Asset(**defaults)


class TestStoreFile:
    def test_copies_file(self, tmp_path: Path) -> None:
        source = tmp_path / "original.png"
        source.write_bytes(b"PNG DATA")

        storage = AssetFileStorage(base_dir=str(tmp_path / "assets"))
        asset = _make_asset()
        file_path = storage.store_file(str(source), asset)

        # Normalize separators for cross-platform (Windows uses backslash)
        assert file_path.replace("\\", "/") == "proj-1/asset-1.png"
        stored = (tmp_path / "assets" / file_path).read_bytes()
        assert stored == b"PNG DATA"

    def test_creates_project_dir(self, tmp_path: Path) -> None:
        source = tmp_path / "test.txt"
        source.write_text("hello")

        storage = AssetFileStorage(base_dir=str(tmp_path / "assets"))
        asset = _make_asset(filename="test.txt")
        storage.store_file(str(source), asset)

        assert (tmp_path / "assets" / "proj-1").is_dir()


class TestStoreBytes:
    def test_writes_bytes(self, tmp_path: Path) -> None:
        storage = AssetFileStorage(base_dir=str(tmp_path / "assets"))
        asset = _make_asset()
        file_path = storage.store_bytes(b"RAW DATA", asset)

        stored = (tmp_path / "assets" / file_path).read_bytes()
        assert stored == b"RAW DATA"


class TestReadFile:
    def test_reads_stored_file(self, tmp_path: Path) -> None:
        storage = AssetFileStorage(base_dir=str(tmp_path / "assets"))
        asset = _make_asset()
        file_path = storage.store_bytes(b"CONTENT", asset)

        result = storage.read_file(file_path)
        assert result == b"CONTENT"


class TestDeleteFile:
    def test_deletes_existing(self, tmp_path: Path) -> None:
        storage = AssetFileStorage(base_dir=str(tmp_path / "assets"))
        asset = _make_asset()
        file_path = storage.store_bytes(b"DATA", asset)

        assert storage.delete_file(file_path) is True
        assert not (tmp_path / "assets" / file_path).exists()

    def test_returns_false_for_missing(self, tmp_path: Path) -> None:
        storage = AssetFileStorage(base_dir=str(tmp_path / "assets"))
        assert storage.delete_file("nonexistent/file.png") is False


class TestComputeHash:
    def test_deterministic(self) -> None:
        h1 = AssetFileStorage.compute_hash(b"hello world")
        h2 = AssetFileStorage.compute_hash(b"hello world")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_different_data_different_hash(self) -> None:
        h1 = AssetFileStorage.compute_hash(b"aaa")
        h2 = AssetFileStorage.compute_hash(b"bbb")
        assert h1 != h2

    def test_from_path(self, tmp_path: Path) -> None:
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")

        h_path = AssetFileStorage.compute_hash_from_path(str(f))
        h_bytes = AssetFileStorage.compute_hash(b"hello world")
        assert h_path == h_bytes

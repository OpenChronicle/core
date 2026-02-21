"""Tests for asset CRUD in SqliteStore — add, get, list, delete, dedup, links."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from openchronicle.core.domain.models.asset import Asset, AssetLink
from openchronicle.core.domain.models.project import Project
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


def _store(tmp_path: Path) -> SqliteStore:
    store = SqliteStore(str(tmp_path / "test.db"))
    store.init_schema()
    return store


def _make_project(store: SqliteStore) -> Project:
    project = Project(id="proj-1", name="test-project")
    store.add_project(project)
    return project


def _make_asset(**overrides: object) -> Asset:
    now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
    defaults = {
        "id": "asset-1",
        "project_id": "proj-1",
        "filename": "photo.png",
        "mime_type": "image/png",
        "file_path": "proj-1/asset-1.png",
        "size_bytes": 12345,
        "content_hash": "abc123",
        "metadata": {"width": 800},
        "created_at": now,
    }
    defaults.update(overrides)
    return Asset(**defaults)  # type: ignore[arg-type]


class TestAddAndGetAsset:
    def test_roundtrip(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        asset = _make_asset()
        store.add_asset(asset)

        fetched = store.get_asset("asset-1")
        assert fetched is not None
        assert fetched.id == "asset-1"
        assert fetched.project_id == "proj-1"
        assert fetched.filename == "photo.png"
        assert fetched.mime_type == "image/png"
        assert fetched.size_bytes == 12345
        assert fetched.content_hash == "abc123"
        assert fetched.metadata == {"width": 800}

    def test_get_nonexistent(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        assert store.get_asset("nope") is None


class TestGetAssetByHash:
    def test_finds_by_hash(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset())

        found = store.get_asset_by_hash("proj-1", "abc123")
        assert found is not None
        assert found.id == "asset-1"

    def test_not_found_different_project(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset())

        assert store.get_asset_by_hash("other-proj", "abc123") is None

    def test_unique_constraint(self, tmp_path: Path) -> None:
        """Same project + content_hash should fail (UNIQUE index)."""
        import sqlite3

        import pytest

        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset())

        dupe = _make_asset(id="asset-2")  # same project_id + content_hash
        with pytest.raises(sqlite3.IntegrityError):
            store.add_asset(dupe)


class TestListAssets:
    def test_lists_by_project(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset(id="a1", content_hash="h1"))
        store.add_asset(_make_asset(id="a2", content_hash="h2"))

        assets = store.list_assets("proj-1")
        assert len(assets) == 2

    def test_limit(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset(id="a1", content_hash="h1"))
        store.add_asset(_make_asset(id="a2", content_hash="h2"))

        assets = store.list_assets("proj-1", limit=1)
        assert len(assets) == 1

    def test_empty_project(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        assert store.list_assets("nonexistent") == []


class TestDeleteAsset:
    def test_deletes_asset_and_links(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset())
        store.add_asset_link(
            AssetLink(id="link-1", asset_id="asset-1", target_type="conversation", target_id="c1", role="input")
        )

        assert store.delete_asset("asset-1") is True
        assert store.get_asset("asset-1") is None
        assert store.list_asset_links(asset_id="asset-1") == []

    def test_returns_false_for_missing(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        assert store.delete_asset("nope") is False


class TestAssetLinks:
    def test_add_and_list_by_asset(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset())

        link = AssetLink(
            id="link-1",
            asset_id="asset-1",
            target_type="conversation",
            target_id="convo-1",
            role="input",
        )
        store.add_asset_link(link)

        links = store.list_asset_links(asset_id="asset-1")
        assert len(links) == 1
        assert links[0].target_type == "conversation"
        assert links[0].role == "input"

    def test_list_by_target(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset())
        store.add_asset_link(
            AssetLink(id="link-1", asset_id="asset-1", target_type="turn", target_id="turn-1", role="output")
        )
        store.add_asset_link(
            AssetLink(id="link-2", asset_id="asset-1", target_type="turn", target_id="turn-2", role="input")
        )

        links = store.list_asset_links(target_type="turn", target_id="turn-1")
        assert len(links) == 1
        assert links[0].id == "link-1"

    def test_delete_link(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        _make_project(store)
        store.add_asset(_make_asset())
        store.add_asset_link(
            AssetLink(id="link-1", asset_id="asset-1", target_type="project", target_id="proj-1", role="avatar")
        )

        assert store.delete_asset_link("link-1") is True
        assert store.list_asset_links(asset_id="asset-1") == []

    def test_delete_missing_link(self, tmp_path: Path) -> None:
        store = _store(tmp_path)
        assert store.delete_asset_link("nope") is False

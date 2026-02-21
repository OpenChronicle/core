"""Tests for Asset and AssetLink domain models."""

from __future__ import annotations

from datetime import UTC, datetime

from openchronicle.core.domain.models.asset import Asset, AssetLink


class TestAsset:
    def test_defaults(self) -> None:
        asset = Asset()
        assert asset.id  # uuid generated
        assert asset.project_id == ""
        assert asset.filename == ""
        assert asset.mime_type == ""
        assert asset.file_path == ""
        assert asset.size_bytes == 0
        assert asset.content_hash == ""
        assert asset.metadata == {}
        assert isinstance(asset.created_at, datetime)

    def test_explicit_fields(self) -> None:
        now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
        asset = Asset(
            id="asset-1",
            project_id="proj-1",
            filename="photo.png",
            mime_type="image/png",
            file_path="proj-1/asset-1.png",
            size_bytes=12345,
            content_hash="abc123",
            metadata={"width": 800},
            created_at=now,
        )
        assert asset.id == "asset-1"
        assert asset.project_id == "proj-1"
        assert asset.filename == "photo.png"
        assert asset.mime_type == "image/png"
        assert asset.size_bytes == 12345
        assert asset.content_hash == "abc123"
        assert asset.metadata == {"width": 800}
        assert asset.created_at == now

    def test_unique_ids(self) -> None:
        a1 = Asset()
        a2 = Asset()
        assert a1.id != a2.id


class TestAssetLink:
    def test_defaults(self) -> None:
        link = AssetLink()
        assert link.id
        assert link.asset_id == ""
        assert link.target_type == ""
        assert link.target_id == ""
        assert link.role == ""
        assert isinstance(link.created_at, datetime)

    def test_explicit_fields(self) -> None:
        now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
        link = AssetLink(
            id="link-1",
            asset_id="asset-1",
            target_type="conversation",
            target_id="convo-1",
            role="input",
            created_at=now,
        )
        assert link.id == "link-1"
        assert link.asset_id == "asset-1"
        assert link.target_type == "conversation"
        assert link.target_id == "convo-1"
        assert link.role == "input"
        assert link.created_at == now

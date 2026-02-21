"""Asset tools — upload, list, get, link."""

from __future__ import annotations

from typing import Any, cast

from mcp.server.fastmcp import Context, FastMCP

from openchronicle.core.application.use_cases import link_asset, upload_asset
from openchronicle.core.domain.models.asset import Asset, AssetLink
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.mcp.tracking import track_tool


def _get_container(ctx: Context) -> CoreContainer:
    return cast(CoreContainer, ctx.request_context.lifespan_context["container"])


def _asset_to_dict(a: Asset) -> dict[str, Any]:
    return {
        "id": a.id,
        "project_id": a.project_id,
        "filename": a.filename,
        "mime_type": a.mime_type,
        "file_path": a.file_path,
        "size_bytes": a.size_bytes,
        "content_hash": a.content_hash,
        "metadata": a.metadata,
        "created_at": a.created_at.isoformat(),
    }


def _link_to_dict(link: AssetLink) -> dict[str, Any]:
    return {
        "id": link.id,
        "asset_id": link.asset_id,
        "target_type": link.target_type,
        "target_id": link.target_id,
        "role": link.role,
        "created_at": link.created_at.isoformat(),
    }


def register(mcp: FastMCP) -> None:
    """Register asset tools on the MCP server."""

    @mcp.tool()
    @track_tool
    def asset_upload(
        project_id: str,
        source_path: str,
        ctx: Context,
        filename: str | None = None,
        mime_type: str | None = None,
        link_target_type: str | None = None,
        link_target_id: str | None = None,
        link_role: str = "reference",
    ) -> dict[str, Any]:
        """Upload a file as an asset with optional immediate linking.

        If the same content already exists in the project, returns the
        existing asset (dedup). A new link is still created if requested.

        Args:
            project_id: Project to store the asset under.
            source_path: Path to the file to upload.
            filename: Override filename (default: basename of source_path).
            mime_type: Override MIME type (default: guessed from extension).
            link_target_type: Optional entity type to link to (e.g. "conversation", "turn").
            link_target_id: Optional entity ID to link to.
            link_role: Link role (default: "reference").
        """
        container = _get_container(ctx)
        asset, is_new = upload_asset.execute(
            store=container.storage,
            file_storage=container.asset_file_storage,
            emit_event=container.event_logger.append,
            project_id=project_id,
            source_path=source_path,
            filename=filename,
            mime_type=mime_type,
            link_target_type=link_target_type,
            link_target_id=link_target_id,
            link_role=link_role,
        )
        result = _asset_to_dict(asset)
        result["is_new"] = is_new
        return result

    @mcp.tool()
    @track_tool
    def asset_list(
        project_id: str,
        ctx: Context,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """List assets in a project.

        Args:
            project_id: Project to list assets for.
            limit: Maximum number of assets to return (None for all).
        """
        container = _get_container(ctx)
        assets = container.storage.list_assets(project_id, limit=limit)
        return [_asset_to_dict(a) for a in assets]

    @mcp.tool()
    @track_tool
    def asset_get(
        asset_id: str,
        ctx: Context,
    ) -> dict[str, Any]:
        """Get asset metadata and its links.

        Args:
            asset_id: The ID of the asset to retrieve.
        """
        container = _get_container(ctx)
        asset = container.storage.get_asset(asset_id)
        if asset is None:
            raise ValueError(f"Asset not found: {asset_id}")
        result = _asset_to_dict(asset)
        links = container.storage.list_asset_links(asset_id=asset_id)
        result["links"] = [_link_to_dict(link) for link in links]
        return result

    @mcp.tool()
    @track_tool
    def asset_link(
        asset_id: str,
        target_type: str,
        target_id: str,
        ctx: Context,
        role: str = "reference",
    ) -> dict[str, Any]:
        """Link an existing asset to any entity.

        Args:
            asset_id: The asset to link.
            target_type: Entity type (e.g. "project", "conversation", "turn", "memory_item").
            target_id: Entity ID.
            role: Link role (e.g. "input", "output", "reference", "avatar").
        """
        container = _get_container(ctx)
        link = link_asset.execute(
            store=container.storage,
            emit_event=container.event_logger.append,
            asset_id=asset_id,
            target_type=target_type,
            target_id=target_id,
            role=role,
        )
        return _link_to_dict(link)

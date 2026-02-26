"""Media generation tools — generate images/video from text prompts."""

from __future__ import annotations

from typing import Any, cast

from mcp.server.fastmcp import Context, FastMCP

from openchronicle.core.application.use_cases import generate_media
from openchronicle.core.domain.models.media import MediaRequest
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.mcp.tracking import track_tool
from openchronicle.interfaces.serializers import asset_to_dict


def _get_container(ctx: Context) -> CoreContainer:
    return cast(CoreContainer, ctx.request_context.lifespan_context["container"])


def register(mcp: FastMCP) -> None:
    """Register media generation tools on the MCP server."""

    @mcp.tool()
    @track_tool
    def media_generate(
        project_id: str,
        prompt: str,
        ctx: Context,
        media_type: str = "image",
        model: str | None = None,
        width: int | None = None,
        height: int | None = None,
        negative_prompt: str | None = None,
        seed: int | None = None,
        steps: int | None = None,
    ) -> dict[str, Any]:
        """Generate an image or video from a text prompt.

        The generated media is stored as an asset in the project.
        Returns asset metadata and generation details.

        Args:
            project_id: Project to store the generated asset under.
            prompt: Text prompt describing the desired media.
            media_type: Type of media to generate ("image" or "video").
            model: Override model name (default: provider's default).
            width: Image width in pixels (provider-dependent).
            height: Image height in pixels (provider-dependent).
            negative_prompt: Things to avoid in generation.
            seed: Random seed for reproducibility.
            steps: Number of diffusion steps.
        """
        container = _get_container(ctx)
        if container.media_port is None:
            return {
                "status": "not_configured",
                "message": "Media generation not configured. Set OC_MEDIA_MODEL to a model name (e.g. 'stub', 'flux', 'gpt-image-1').",
            }

        # Clamp numeric inputs (MCP callers are LLM agents)
        if width is not None:
            width = max(64, min(width, 4096))
        if height is not None:
            height = max(64, min(height, 4096))
        if steps is not None:
            steps = max(1, min(steps, 200))

        request = MediaRequest(
            prompt=prompt.strip(),
            media_type=media_type,
            model=model,
            width=width,
            height=height,
            negative_prompt=negative_prompt,
            seed=seed,
            steps=steps,
        )

        result, asset, is_new = generate_media.execute(
            media_port=container.media_port,
            asset_store=container.storage,
            file_storage=container.asset_file_storage,
            emit_event=container.emit_event,
            project_id=project_id,
            request=request,
        )

        asset_dict = asset_to_dict(asset)
        asset_dict["is_new"] = is_new
        asset_dict["generation"] = {
            "model": result.model,
            "provider": result.provider,
            "media_type": result.media_type,
            "latency_ms": result.latency_ms,
            "seed": result.seed,
        }
        return asset_dict

"""Media generation routes — generate images/video from text prompts."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from openchronicle.core.application.use_cases import generate_media
from openchronicle.core.domain.models.media import MediaRequest
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.api.deps import get_container
from openchronicle.interfaces.serializers import asset_to_dict

router = APIRouter(prefix="/media")

ContainerDep = Annotated[CoreContainer, Depends(get_container)]


class MediaGenerateRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=10_000)
    media_type: str = Field(default="image", pattern=r"^(image|video)$")
    model: str | None = Field(default=None, max_length=200)
    width: int | None = Field(default=None, ge=64, le=4096)
    height: int | None = Field(default=None, ge=64, le=4096)
    negative_prompt: str | None = Field(default=None, max_length=10_000)
    seed: int | None = Field(default=None)
    steps: int | None = Field(default=None, ge=1, le=200)


@router.post("/generate")
def media_generate(
    body: MediaGenerateRequest,
    container: ContainerDep,
) -> dict[str, Any]:
    """Generate media from a text prompt and store as an asset."""
    if container.media_port is None:
        raise HTTPException(
            status_code=503,
            detail="Media generation not configured. Set OC_MEDIA_MODEL to a model name (e.g. 'stub', 'flux', 'gpt-image-1').",
        )

    request = MediaRequest(
        prompt=body.prompt.strip(),
        media_type=body.media_type,
        model=body.model,
        width=body.width,
        height=body.height,
        negative_prompt=body.negative_prompt,
        seed=body.seed,
        steps=body.steps,
    )

    result, asset, is_new = generate_media.execute(
        media_port=container.media_port,
        asset_store=container.storage,
        file_storage=container.asset_file_storage,
        emit_event=container.emit_event,
        project_id=body.project_id,
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

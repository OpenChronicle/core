"""Generate media — orchestrate port + asset storage + event emission."""

from __future__ import annotations

import logging
from collections.abc import Callable

from openchronicle.core.application.services.asset_storage import AssetFileStorage
from openchronicle.core.domain.exceptions import ValidationError
from openchronicle.core.domain.models.asset import Asset, AssetLink
from openchronicle.core.domain.models.media import MediaRequest, MediaResult
from openchronicle.core.domain.models.project import Event
from openchronicle.core.domain.ports.asset_store_port import AssetStorePort
from openchronicle.core.domain.ports.media_generation_port import MediaGenerationPort

_logger = logging.getLogger(__name__)

_MIME_EXTENSIONS: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
}


def execute(
    media_port: MediaGenerationPort,
    asset_store: AssetStorePort,
    file_storage: AssetFileStorage,
    emit_event: Callable[[Event], None],
    *,
    project_id: str,
    request: MediaRequest,
    link_target_type: str | None = None,
    link_target_id: str | None = None,
    link_role: str = "output",
) -> tuple[MediaResult, Asset, bool]:
    """Generate media, store as asset, optionally link.

    Returns ``(result, asset, is_new)``.  If the same content hash
    already exists in the project, returns the existing asset
    (``is_new=False``) to avoid duplicate storage.
    """
    if not request.prompt.strip():
        raise ValidationError("Media generation prompt must not be empty")

    if request.media_type not in media_port.supported_media_types():
        raise ValidationError(
            f"Media type '{request.media_type}' not supported by "
            f"{media_port.model_name()}. Supported: {media_port.supported_media_types()}"
        )

    _logger.info(
        "Generating %s: model=%s, prompt=%.60s...",
        request.media_type,
        media_port.model_name(),
        request.prompt,
    )

    result = media_port.generate(request)

    # Store as asset with dedup
    content_hash = file_storage.compute_hash(result.data)
    ext = _MIME_EXTENSIONS.get(result.mime_type, "")
    filename = f"generated_{result.media_type}{ext}"

    existing = asset_store.get_asset_by_hash(project_id, content_hash)
    if existing is not None:
        if link_target_type and link_target_id:
            link = AssetLink(
                asset_id=existing.id,
                target_type=link_target_type,
                target_id=link_target_id,
                role=link_role,
            )
            asset_store.add_asset_link(link)
        return result, existing, False

    asset = Asset(
        project_id=project_id,
        filename=filename,
        mime_type=result.mime_type,
        size_bytes=len(result.data),
        content_hash=content_hash,
        metadata={
            "prompt": request.prompt,
            "model": result.model,
            "provider": result.provider,
            "seed": result.seed,
            "latency_ms": result.latency_ms,
        },
    )

    file_path = file_storage.store_bytes(result.data, asset)
    asset.file_path = file_path
    asset_store.add_asset(asset)

    emit_event(
        Event(
            project_id=project_id,
            type="media.generated",
            payload={
                "asset_id": asset.id,
                "media_type": result.media_type,
                "mime_type": result.mime_type,
                "model": result.model,
                "provider": result.provider,
                "size_bytes": len(result.data),
                "latency_ms": result.latency_ms,
                "seed": result.seed,
                "prompt_preview": request.prompt[:100],
            },
        )
    )

    if link_target_type and link_target_id:
        link = AssetLink(
            asset_id=asset.id,
            target_type=link_target_type,
            target_id=link_target_id,
            role=link_role,
        )
        asset_store.add_asset_link(link)
        emit_event(
            Event(
                project_id=project_id,
                type="asset.linked",
                payload={
                    "asset_id": asset.id,
                    "link_id": link.id,
                    "target_type": link_target_type,
                    "target_id": link_target_id,
                    "role": link_role,
                },
            )
        )

    return result, asset, True

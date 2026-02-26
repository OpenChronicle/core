"""Media CLI commands: media generate."""

from __future__ import annotations

import argparse

from openchronicle.core.application.use_cases import generate_media
from openchronicle.core.domain.models.media import MediaRequest
from openchronicle.core.infrastructure.wiring.container import CoreContainer


def cmd_media(args: argparse.Namespace, container: CoreContainer) -> int:
    """Dispatch to media subcommands."""
    from collections.abc import Callable

    media_dispatch: dict[str, Callable[[argparse.Namespace, CoreContainer], int]] = {
        "generate": cmd_media_generate,
    }
    handler = media_dispatch.get(args.media_command)
    if handler is None:
        print("Usage: oc media <subcommand>")
        return 1
    return handler(args, container)


def cmd_media_generate(args: argparse.Namespace, container: CoreContainer) -> int:
    if container.media_port is None:
        print("Media generation not configured. Set OC_MEDIA_MODEL (e.g. stub, flux, gpt-image-1).")
        return 1

    request = MediaRequest(
        prompt=args.prompt,
        media_type=args.media_type,
        model=args.model,
        width=args.width,
        height=args.height,
        negative_prompt=args.negative_prompt,
        seed=args.seed,
        steps=args.steps,
    )

    try:
        result, asset, is_new = generate_media.execute(
            media_port=container.media_port,
            asset_store=container.storage,
            file_storage=container.asset_file_storage,
            emit_event=container.emit_event,
            project_id=args.project_id,
            request=request,
        )
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    status = "new" if is_new else "dedup"
    print(f"asset_id: {asset.id}")
    print(f"status: {status}")
    print(f"model: {result.model}")
    print(f"provider: {result.provider}")
    print(f"mime_type: {result.mime_type}")
    print(f"size_bytes: {len(result.data)}")
    print(f"latency_ms: {result.latency_ms:.0f}")
    print(f"file_path: {asset.file_path}")
    if result.seed is not None:
        print(f"seed: {result.seed}")
    return 0

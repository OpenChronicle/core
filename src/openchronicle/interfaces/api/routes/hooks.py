"""Inbound hooks — generic endpoint for external webhook POSTs dispatched to plugin handlers."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from openchronicle.core.application.use_cases import task_submit
from openchronicle.core.domain.exceptions import NotFoundError
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.api.deps import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hooks")

ContainerDep = Annotated[CoreContainer, Depends(get_container)]


async def _execute_hook_task(container: CoreContainer, task_id: str) -> None:
    """Background callback: execute the submitted task."""
    try:
        await container.orchestrator.execute_task(task_id)
    except Exception:
        logger.exception("Hook task %s failed", task_id)


async def _parse_body(request: Request) -> dict[str, Any]:
    """Parse JSON or multipart form-data into a dict.

    Plex sends multipart with a ``payload`` JSON field (+ optional ``thumb``
    image).  Other services typically send plain JSON.
    """
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        payload_field = form.get("payload")
        if payload_field is not None:
            import json

            raw = payload_field if isinstance(payload_field, str) else await payload_field.read()  # type: ignore[union-attr,unused-ignore]
            text = raw if isinstance(raw, str) else raw.decode("utf-8")
            parsed: dict[str, Any] = json.loads(text)
            return parsed
        # Fallback: convert all form fields to a dict
        return {k: v for k, v in form.items() if not isinstance(v, UploadFile)}

    # Default: assume JSON
    result: dict[str, Any] = await request.json()
    return result


@router.post(
    "/{handler_name}",
    status_code=202,
    response_class=JSONResponse,
)
async def inbound_hook(
    handler_name: Annotated[str, Path(min_length=1, max_length=200)],
    project_id: Annotated[str, Query(min_length=1, max_length=200)],
    request: Request,
    background_tasks: BackgroundTasks,
    container: ContainerDep,
) -> dict[str, str]:
    """Receive an external webhook POST and dispatch to a plugin handler.

    Returns 202 immediately; execution happens in the background.
    """
    # Validate handler exists
    handler = container.orchestrator.handler_registry.get(handler_name)
    if handler is None:
        raise NotFoundError(f"Unknown handler: {handler_name}")

    body = await _parse_body(request)

    task = task_submit.execute(
        orchestrator=container.orchestrator,
        project_id=project_id,
        task_type="plugin.invoke",
        payload={"handler": handler_name, "input": {"webhook_payload": body}},
    )

    background_tasks.add_task(_execute_hook_task, container, task.id)

    return {"task_id": task.id}

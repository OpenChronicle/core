"""Webhook routes — register, list, get, delete, deliveries."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, Field

from openchronicle.core.application.use_cases import delete_webhook, list_webhooks, register_webhook
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.api.deps import get_container
from openchronicle.interfaces.serializers import delivery_to_dict, webhook_to_dict

router = APIRouter(prefix="/webhook")

ContainerDep = Annotated[CoreContainer, Depends(get_container)]


class WebhookRegisterRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2048)
    event_filter: str = Field(default="*", min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


@router.post("", status_code=201)
def webhook_register(
    body: WebhookRegisterRequest,
    container: ContainerDep,
) -> dict[str, Any]:
    """Register a new webhook subscription."""
    sub = register_webhook.execute(
        webhook_service=container.webhook_service,
        emit_event=container.emit_event,
        project_id=body.project_id,
        url=body.url,
        event_filter=body.event_filter,
        description=body.description,
    )
    # Ensure dispatcher is running now that we have a subscription
    container.ensure_webhook_dispatcher()
    return webhook_to_dict(sub)


@router.get("")
def webhook_list(
    container: ContainerDep,
    project_id: str | None = Query(default=None, min_length=1, max_length=200),
    active_only: bool = Query(default=False),
) -> list[dict[str, Any]]:
    """List webhook subscriptions."""
    result = list_webhooks.execute(
        webhook_service=container.webhook_service,
        project_id=project_id,
        active_only=active_only,
    )
    return [webhook_to_dict(s) for s in result]


@router.get("/{webhook_id}")
def webhook_get(
    webhook_id: Annotated[str, Path(min_length=1, max_length=200)],
    container: ContainerDep,
) -> dict[str, Any]:
    """Get a single webhook subscription."""
    sub = container.webhook_service.get(webhook_id)
    return webhook_to_dict(sub)


@router.delete("/{webhook_id}", status_code=204)
def webhook_delete(
    webhook_id: Annotated[str, Path(min_length=1, max_length=200)],
    container: ContainerDep,
) -> None:
    """Delete a webhook subscription."""
    delete_webhook.execute(
        webhook_service=container.webhook_service,
        emit_event=container.emit_event,
        subscription_id=webhook_id,
    )


@router.get("/{webhook_id}/deliveries")
def webhook_deliveries(
    webhook_id: Annotated[str, Path(min_length=1, max_length=200)],
    container: ContainerDep,
    limit: int = Query(default=50, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """List delivery attempts for a webhook subscription."""
    # Verify subscription exists
    container.webhook_service.get(webhook_id)
    deliveries = container.storage.list_deliveries(webhook_id, limit=limit)
    return [delivery_to_dict(d) for d in deliveries]

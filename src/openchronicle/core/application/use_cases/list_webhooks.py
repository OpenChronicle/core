"""List webhook subscriptions."""

from __future__ import annotations

from openchronicle.core.application.services.webhook_service import WebhookService
from openchronicle.core.domain.models.webhook import WebhookSubscription


def execute(
    webhook_service: WebhookService,
    *,
    project_id: str | None = None,
    active_only: bool = False,
) -> list[WebhookSubscription]:
    return webhook_service.list(project_id=project_id, active_only=active_only)

"""Register a new webhook subscription."""

from __future__ import annotations

import logging
from collections.abc import Callable

from openchronicle.core.application.services.webhook_service import WebhookService
from openchronicle.core.domain.models.project import Event
from openchronicle.core.domain.models.webhook import WebhookSubscription

_logger = logging.getLogger(__name__)


def execute(
    webhook_service: WebhookService,
    emit_event: Callable[[Event], None],
    *,
    project_id: str,
    url: str,
    event_filter: str = "*",
    description: str = "",
) -> WebhookSubscription:
    sub = webhook_service.register(
        project_id=project_id,
        url=url,
        event_filter=event_filter,
        description=description,
    )
    _logger.info("Webhook registered: %s → %s (filter=%s)", sub.id, sub.url, sub.event_filter)
    emit_event(
        Event(
            project_id=project_id,
            type="webhook.registered",
            payload={
                "subscription_id": sub.id,
                "url": sub.url,
                "event_filter": sub.event_filter,
                "description": sub.description,
            },
        )
    )
    return sub

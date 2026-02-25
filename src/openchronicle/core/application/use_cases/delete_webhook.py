"""Delete a webhook subscription."""

from __future__ import annotations

import logging
from collections.abc import Callable

from openchronicle.core.application.services.webhook_service import WebhookService
from openchronicle.core.domain.models.project import Event

_logger = logging.getLogger(__name__)


def execute(
    webhook_service: WebhookService,
    emit_event: Callable[[Event], None],
    *,
    subscription_id: str,
) -> None:
    # Get the subscription first to extract project_id for the event
    sub = webhook_service.get(subscription_id)
    webhook_service.delete(subscription_id)
    _logger.info("Webhook deleted: %s", subscription_id)
    emit_event(
        Event(
            project_id=sub.project_id,
            type="webhook.deleted",
            payload={"subscription_id": subscription_id},
        )
    )

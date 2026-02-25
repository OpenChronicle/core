"""Webhook subscription and delivery attempt domain models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from openchronicle.core.domain.time_utils import utc_now


@dataclass
class WebhookSubscription:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    url: str = ""
    secret: str = ""
    event_filter: str = "*"
    active: bool = True
    created_at: datetime = field(default_factory=utc_now)
    description: str = ""


@dataclass
class DeliveryAttempt:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subscription_id: str = ""
    event_id: str = ""
    status_code: int | None = None
    success: bool = False
    attempt_number: int = 1
    error_message: str | None = None
    delivered_at: datetime = field(default_factory=utc_now)

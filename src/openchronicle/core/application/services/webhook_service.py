"""Webhook service — subscription CRUD, HMAC signing, filter matching, delivery."""

from __future__ import annotations

import fnmatch
import hashlib
import hmac
import logging
import secrets
from collections.abc import Callable

import httpx

from openchronicle.core.domain.errors.error_codes import WEBHOOK_NOT_FOUND
from openchronicle.core.domain.exceptions import NotFoundError
from openchronicle.core.domain.exceptions import ValidationError as DomainValidationError
from openchronicle.core.domain.models.project import Event
from openchronicle.core.domain.models.webhook import DeliveryAttempt, WebhookSubscription
from openchronicle.core.domain.ports.webhook_store_port import WebhookStorePort
from openchronicle.core.domain.time_utils import utc_now

_logger = logging.getLogger(__name__)

_DELIVERY_TIMEOUT = 10.0  # seconds


class WebhookService:
    def __init__(self, store: WebhookStorePort) -> None:
        self.store = store

    # ── Subscription CRUD ───────────────────────────────────────────

    def register(
        self,
        project_id: str,
        url: str,
        event_filter: str = "*",
        description: str = "",
    ) -> WebhookSubscription:
        if not url or not url.startswith(("http://", "https://")):
            raise DomainValidationError(f"Invalid webhook URL: {url}")
        # Validate filter syntax: must be a valid glob
        if not event_filter:
            raise DomainValidationError("Event filter must not be empty")
        sub = WebhookSubscription(
            project_id=project_id,
            url=url,
            secret=secrets.token_hex(32),
            event_filter=event_filter,
            description=description,
        )
        self.store.add_subscription(sub)
        return sub

    def delete(self, subscription_id: str) -> None:
        self.store.delete_subscription(subscription_id)

    def list(self, project_id: str | None = None, active_only: bool = False) -> list[WebhookSubscription]:
        return self.store.list_subscriptions(project_id=project_id, active_only=active_only)

    def get(self, subscription_id: str) -> WebhookSubscription:
        sub = self.store.get_subscription(subscription_id)
        if sub is None:
            raise NotFoundError(f"Webhook not found: {subscription_id}", code=WEBHOOK_NOT_FOUND)
        return sub

    def update(
        self,
        subscription_id: str,
        *,
        active: bool | None = None,
        url: str | None = None,
        event_filter: str | None = None,
    ) -> None:
        if url is not None and not url.startswith(("http://", "https://")):
            raise DomainValidationError(f"Invalid webhook URL: {url}")
        self.store.update_subscription(subscription_id, active=active, url=url, event_filter=event_filter)

    # ── HMAC signing ────────────────────────────────────────────────

    @staticmethod
    def sign_payload(secret: str, payload: bytes) -> str:
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    # ── Filter matching ─────────────────────────────────────────────

    @staticmethod
    def matches_filter(event_type: str, filter_pattern: str) -> bool:
        return fnmatch.fnmatch(event_type, filter_pattern)

    # ── Delivery ────────────────────────────────────────────────────

    def deliver(
        self,
        subscription: WebhookSubscription,
        event: Event,
        emit_event: Callable[[Event], None] | None = None,
    ) -> DeliveryAttempt:
        """Deliver a single event to a webhook endpoint. Synchronous."""
        import json

        payload_dict = {
            "event_id": event.id,
            "event_type": event.type,
            "project_id": event.project_id,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }
        payload_bytes = json.dumps(payload_dict, sort_keys=True).encode()
        signature = self.sign_payload(subscription.secret, payload_bytes)

        attempt = DeliveryAttempt(
            subscription_id=subscription.id,
            event_id=event.id,
            delivered_at=utc_now(),
        )

        try:
            resp = httpx.post(
                subscription.url,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-OC-Signature-256": f"sha256={signature}",
                    "X-OC-Event": event.type,
                },
                timeout=_DELIVERY_TIMEOUT,
            )
            attempt.status_code = resp.status_code
            attempt.success = 200 <= resp.status_code < 300
            if not attempt.success:
                attempt.error_message = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            attempt.success = False
            attempt.error_message = str(exc)[:500]
            _logger.warning("Webhook delivery failed for %s: %s", subscription.id, exc)

        self.store.add_delivery(attempt)
        return attempt

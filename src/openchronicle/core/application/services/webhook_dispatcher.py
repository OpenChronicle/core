"""Webhook dispatcher — background delivery thread fed by queue."""

from __future__ import annotations

import logging
import queue
import random
import threading
import time

from openchronicle.core.application.services.webhook_service import WebhookService
from openchronicle.core.domain.models.project import Event
from openchronicle.core.domain.ports.webhook_store_port import WebhookStorePort

_logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BASE_DELAY_S = 10.0  # 10s, 30s, 90s with backoff multiplier 3x
_BACKOFF_MULTIPLIER = 3.0
_JITTER_FACTOR = 0.25

_SENTINEL = object()


class WebhookDispatcher:
    """Dispatch events to webhook subscribers via a background thread."""

    def __init__(self, webhook_service: WebhookService, store: WebhookStorePort) -> None:
        self.webhook_service = webhook_service
        self.store = store
        self._queue: queue.Queue[object] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._started = False

    def enqueue(self, event: Event) -> None:
        """Drop event onto the queue. Non-blocking."""
        self._queue.put(event)

    def start(self) -> None:
        """Start the background delivery thread (daemon)."""
        if self._started:
            return
        self._thread = threading.Thread(target=self._delivery_loop, daemon=True, name="oc-webhook-dispatcher")
        self._started = True
        self._thread.start()
        _logger.info("Webhook dispatcher started")

    def stop(self, timeout: float = 5.0) -> None:
        """Signal thread to stop and wait."""
        if not self._started:
            return
        self._queue.put(_SENTINEL)
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._started = False
        _logger.info("Webhook dispatcher stopped")

    def _delivery_loop(self) -> None:
        """Thread target: drain queue, match subscriptions, deliver."""
        while True:
            try:
                item = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if item is _SENTINEL:
                break

            if not isinstance(item, Event):
                continue

            try:
                self._process_event(item)
            except Exception:  # noqa: BLE001
                _logger.exception("Error processing event %s for webhooks", item.id)

    def _process_event(self, event: Event) -> None:
        """Match active subscriptions, deliver to each, retry on failure."""
        # Prevent recursion: don't dispatch webhook.* events
        if event.type.startswith("webhook."):
            return

        subscriptions = self.store.list_subscriptions(active_only=True)
        for sub in subscriptions:
            if not self.webhook_service.matches_filter(event.type, sub.event_filter):
                continue

            attempt = self.webhook_service.deliver(sub, event)
            if attempt.success:
                continue

            # Retry with exponential backoff
            for retry_num in range(2, _MAX_RETRIES + 1):
                delay = _BASE_DELAY_S * (_BACKOFF_MULTIPLIER ** (retry_num - 1))
                jitter = delay * _JITTER_FACTOR * random.uniform(-1, 1)
                time.sleep(delay + jitter)

                attempt = self.webhook_service.deliver(sub, event)
                attempt.attempt_number = retry_num
                if attempt.success:
                    break

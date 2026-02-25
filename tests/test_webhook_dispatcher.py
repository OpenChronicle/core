"""Tests for WebhookDispatcher and composite emit_event."""

from __future__ import annotations

import time
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from openchronicle.core.application.services.webhook_dispatcher import WebhookDispatcher
from openchronicle.core.application.services.webhook_service import WebhookService
from openchronicle.core.domain.models.project import Event, Project
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


@pytest.fixture()
def store() -> SqliteStore:
    s = SqliteStore(db_path=":memory:")
    s.init_schema()
    s.add_project(Project(id="proj-1", name="Test"))
    return s


@pytest.fixture()
def service(store: SqliteStore) -> WebhookService:
    return WebhookService(store=store)


@pytest.fixture()
def dispatcher(service: WebhookService, store: SqliteStore) -> Generator[WebhookDispatcher]:
    d = WebhookDispatcher(webhook_service=service, store=store)
    yield d
    if d._started:
        d.stop(timeout=2.0)


def test_enqueue_adds_event_to_queue(dispatcher: WebhookDispatcher) -> None:
    event = Event(project_id="proj-1", type="llm.requested")
    dispatcher.enqueue(event)
    assert not dispatcher._queue.empty()


def test_start_creates_daemon_thread(dispatcher: WebhookDispatcher) -> None:
    dispatcher.start()
    assert dispatcher._started is True
    assert dispatcher._thread is not None
    assert dispatcher._thread.daemon is True
    assert dispatcher._thread.is_alive()


def test_stop_signals_thread_to_exit(dispatcher: WebhookDispatcher) -> None:
    dispatcher.start()
    dispatcher.stop(timeout=2.0)
    assert dispatcher._started is False


def test_process_event_matches_subscriptions(service: WebhookService, store: SqliteStore) -> None:
    sub = service.register("proj-1", "https://example.com/hook", "llm.*")
    dispatcher = WebhookDispatcher(webhook_service=service, store=store)

    event = Event(project_id="proj-1", type="llm.requested", payload={"model": "gpt-4"})

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("openchronicle.core.application.services.webhook_service.httpx.post", return_value=mock_resp):
        dispatcher._process_event(event)

    deliveries = store.list_deliveries(sub.id)
    assert len(deliveries) == 1
    assert deliveries[0].success is True


def test_process_event_skips_inactive_subscriptions(service: WebhookService, store: SqliteStore) -> None:
    sub = service.register("proj-1", "https://example.com/hook", "llm.*")
    service.update(sub.id, active=False)
    dispatcher = WebhookDispatcher(webhook_service=service, store=store)

    event = Event(project_id="proj-1", type="llm.requested")

    with patch("openchronicle.core.application.services.webhook_service.httpx.post") as mock_post:
        dispatcher._process_event(event)
        mock_post.assert_not_called()


def test_process_event_skips_webhook_events(service: WebhookService, store: SqliteStore) -> None:
    """Webhook events should not trigger dispatch (recursion prevention)."""
    service.register("proj-1", "https://example.com/hook", "*")
    dispatcher = WebhookDispatcher(webhook_service=service, store=store)

    event = Event(project_id="proj-1", type="webhook.registered")

    with patch("openchronicle.core.application.services.webhook_service.httpx.post") as mock_post:
        dispatcher._process_event(event)
        mock_post.assert_not_called()


def test_process_event_retries_on_failure(service: WebhookService, store: SqliteStore) -> None:
    sub = service.register("proj-1", "https://example.com/hook", "llm.*")
    dispatcher = WebhookDispatcher(webhook_service=service, store=store)

    event = Event(project_id="proj-1", type="llm.requested")

    with (
        patch(
            "openchronicle.core.application.services.webhook_service.httpx.post",
            side_effect=Exception("timeout"),
        ),
        patch("openchronicle.core.application.services.webhook_dispatcher.time.sleep"),
    ):
        dispatcher._process_event(event)

    # Should have 3 deliveries: initial + 2 retries
    deliveries = store.list_deliveries(sub.id)
    assert len(deliveries) == 3


def test_process_event_records_delivery_attempts(service: WebhookService, store: SqliteStore) -> None:
    sub = service.register("proj-1", "https://example.com/hook", "llm.*")
    dispatcher = WebhookDispatcher(webhook_service=service, store=store)

    event = Event(project_id="proj-1", type="llm.requested")
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("openchronicle.core.application.services.webhook_service.httpx.post", return_value=mock_resp):
        dispatcher._process_event(event)

    deliveries = store.list_deliveries(sub.id)
    assert len(deliveries) == 1
    assert deliveries[0].event_id == event.id


def test_composite_emit_calls_both(store: SqliteStore) -> None:
    """Test the container's composite emit pattern."""
    from openchronicle.core.infrastructure.logging.event_logger import EventLogger

    event_logger = EventLogger(store)
    service = WebhookService(store=store)
    dispatcher = WebhookDispatcher(webhook_service=service, store=store)

    # Track calls
    logger_calls: list[Event] = []
    original_append = event_logger.append

    def tracking_append(event: Event) -> None:
        logger_calls.append(event)
        original_append(event)

    dispatcher_calls: list[Event] = []
    original_enqueue = dispatcher.enqueue

    def tracking_enqueue(event: Event) -> None:
        dispatcher_calls.append(event)
        original_enqueue(event)

    def composite_emit(event: Event) -> None:
        tracking_append(event)
        tracking_enqueue(event)

    event = Event(project_id="proj-1", type="test.event")
    composite_emit(event)

    assert len(logger_calls) == 1
    assert len(dispatcher_calls) == 1


def test_composite_emit_works_without_dispatcher() -> None:
    """Composite pattern degrades gracefully when no dispatcher configured."""
    calls: list[Event] = []

    dispatcher = None

    def composite_emit(event: Event) -> None:
        calls.append(event)
        if dispatcher is not None:
            dispatcher.enqueue(event)

    event = Event(project_id="proj-1", type="test.event")
    composite_emit(event)
    assert len(calls) == 1


def test_dispatcher_handles_empty_queue(dispatcher: WebhookDispatcher) -> None:
    """Dispatcher thread should handle empty queue gracefully (timeout loop)."""
    dispatcher.start()
    time.sleep(0.2)  # Let it loop a few times on empty queue
    assert dispatcher._thread is not None
    assert dispatcher._thread.is_alive()


def test_dispatcher_handles_delivery_errors_without_crashing(service: WebhookService, store: SqliteStore) -> None:
    service.register("proj-1", "https://example.com/hook", "*")
    dispatcher = WebhookDispatcher(webhook_service=service, store=store)

    event = Event(project_id="proj-1", type="llm.error")

    # Even with delivery failure, _process_event should not raise
    with (
        patch(
            "openchronicle.core.application.services.webhook_service.httpx.post",
            side_effect=Exception("network error"),
        ),
        patch("openchronicle.core.application.services.webhook_dispatcher.time.sleep"),
    ):
        dispatcher._process_event(event)  # Should not raise

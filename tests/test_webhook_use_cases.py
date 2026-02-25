"""Tests for webhook use cases."""

from __future__ import annotations

import pytest

from openchronicle.core.application.services.webhook_service import WebhookService
from openchronicle.core.application.use_cases import delete_webhook, list_webhooks, register_webhook
from openchronicle.core.domain.exceptions import NotFoundError
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
def events() -> list[Event]:
    return []


def _collector(events: list[Event]) -> object:
    return events.append


def test_register_creates_subscription(service: WebhookService, events: list[Event]) -> None:
    sub = register_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        project_id="proj-1",
        url="https://example.com/hook",
        event_filter="llm.*",
        description="LLM events",
    )
    assert sub.url == "https://example.com/hook"
    assert sub.event_filter == "llm.*"


def test_register_validates_required_fields(service: WebhookService, events: list[Event]) -> None:
    from openchronicle.core.domain.exceptions import ValidationError as DomainValidationError

    with pytest.raises(DomainValidationError):
        register_webhook.execute(
            webhook_service=service,
            emit_event=events.append,
            project_id="proj-1",
            url="",
        )


def test_register_emits_event(service: WebhookService, events: list[Event]) -> None:
    sub = register_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        project_id="proj-1",
        url="https://example.com/hook",
    )
    assert len(events) == 1
    assert events[0].type == "webhook.registered"
    assert events[0].payload["subscription_id"] == sub.id
    assert events[0].payload["url"] == sub.url


def test_list_returns_all(service: WebhookService, events: list[Event]) -> None:
    register_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        project_id="proj-1",
        url="https://example.com/a",
    )
    register_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        project_id="proj-1",
        url="https://example.com/b",
    )
    result = list_webhooks.execute(webhook_service=service)
    assert len(result) == 2


def test_list_empty(service: WebhookService) -> None:
    result = list_webhooks.execute(webhook_service=service)
    assert result == []


def test_delete_removes_and_emits(service: WebhookService, events: list[Event]) -> None:
    sub = register_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        project_id="proj-1",
        url="https://example.com/hook",
    )
    events.clear()
    delete_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        subscription_id=sub.id,
    )
    assert len(events) == 1
    assert events[0].type == "webhook.deleted"
    assert events[0].payload["subscription_id"] == sub.id


def test_delete_nonexistent_raises_not_found(service: WebhookService, events: list[Event]) -> None:
    with pytest.raises(NotFoundError):
        delete_webhook.execute(
            webhook_service=service,
            emit_event=events.append,
            subscription_id="nonexistent",
        )


def test_register_emits_event_with_details(service: WebhookService, events: list[Event]) -> None:
    register_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        project_id="proj-1",
        url="https://example.com/hook",
        event_filter="task.*",
        description="Task events",
    )
    evt = events[0]
    assert evt.payload["event_filter"] == "task.*"
    assert evt.payload["description"] == "Task events"


def test_delete_emits_event_with_subscription_id(service: WebhookService, events: list[Event]) -> None:
    sub = register_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        project_id="proj-1",
        url="https://example.com/hook",
    )
    events.clear()
    delete_webhook.execute(
        webhook_service=service,
        emit_event=events.append,
        subscription_id=sub.id,
    )
    assert events[0].payload["subscription_id"] == sub.id

"""Tests for webhook persistence in SqliteStore."""

from __future__ import annotations

from typing import Any

import pytest

from openchronicle.core.domain.exceptions import NotFoundError
from openchronicle.core.domain.models.project import Project
from openchronicle.core.domain.models.webhook import DeliveryAttempt, WebhookSubscription
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


@pytest.fixture()
def store(tmp_path: object) -> SqliteStore:
    s = SqliteStore(db_path=":memory:")
    s.init_schema()
    # Create referenced project
    s.add_project(Project(id="proj-1", name="Test Project"))
    s.add_project(Project(id="proj-2", name="Test Project 2"))
    return s


def _make_sub(**kwargs: Any) -> WebhookSubscription:
    defaults: dict[str, Any] = {
        "project_id": "proj-1",
        "url": "https://example.com/hook",
        "secret": "s3cret",
        "event_filter": "llm.*",
        "description": "test hook",
    }
    defaults.update(kwargs)
    return WebhookSubscription(**defaults)


def test_add_and_get_subscription(store: SqliteStore) -> None:
    sub = _make_sub()
    store.add_subscription(sub)
    got = store.get_subscription(sub.id)
    assert got is not None
    assert got.id == sub.id
    assert got.project_id == sub.project_id
    assert got.url == sub.url
    assert got.secret == sub.secret
    assert got.event_filter == sub.event_filter
    assert got.active is True
    assert got.description == sub.description


def test_list_subscriptions_all(store: SqliteStore) -> None:
    store.add_subscription(_make_sub())
    store.add_subscription(_make_sub(project_id="proj-2"))
    assert len(store.list_subscriptions()) == 2


def test_list_subscriptions_by_project(store: SqliteStore) -> None:
    store.add_subscription(_make_sub())
    store.add_subscription(_make_sub(project_id="proj-2"))
    result = store.list_subscriptions(project_id="proj-1")
    assert len(result) == 1
    assert result[0].project_id == "proj-1"


def test_list_subscriptions_active_only(store: SqliteStore) -> None:
    store.add_subscription(_make_sub())
    store.add_subscription(_make_sub(active=False))
    result = store.list_subscriptions(active_only=True)
    assert len(result) == 1
    assert result[0].active is True


def test_delete_subscription(store: SqliteStore) -> None:
    sub = _make_sub()
    store.add_subscription(sub)
    store.delete_subscription(sub.id)
    assert store.get_subscription(sub.id) is None


def test_delete_cascade_removes_deliveries(store: SqliteStore) -> None:
    sub = _make_sub()
    store.add_subscription(sub)
    attempt = DeliveryAttempt(subscription_id=sub.id, event_id="evt-1", success=True, status_code=200)
    store.add_delivery(attempt)
    assert len(store.list_deliveries(sub.id)) == 1
    store.delete_subscription(sub.id)
    assert len(store.list_deliveries(sub.id)) == 0


def test_update_subscription_active_toggle(store: SqliteStore) -> None:
    sub = _make_sub()
    store.add_subscription(sub)
    store.update_subscription(sub.id, active=False)
    got = store.get_subscription(sub.id)
    assert got is not None
    assert got.active is False


def test_update_subscription_url_and_filter(store: SqliteStore) -> None:
    sub = _make_sub()
    store.add_subscription(sub)
    store.update_subscription(sub.id, url="https://new.example.com", event_filter="task.*")
    got = store.get_subscription(sub.id)
    assert got is not None
    assert got.url == "https://new.example.com"
    assert got.event_filter == "task.*"


def test_add_and_list_deliveries(store: SqliteStore) -> None:
    sub = _make_sub()
    store.add_subscription(sub)
    for i in range(3):
        store.add_delivery(
            DeliveryAttempt(
                subscription_id=sub.id,
                event_id=f"evt-{i}",
                success=i == 0,
                status_code=200 if i == 0 else 500,
                attempt_number=i + 1,
            )
        )
    deliveries = store.list_deliveries(sub.id, limit=2)
    assert len(deliveries) == 2


def test_get_returns_none_for_missing(store: SqliteStore) -> None:
    assert store.get_subscription("nonexistent") is None


def test_delete_nonexistent_raises_not_found(store: SqliteStore) -> None:
    with pytest.raises(NotFoundError):
        store.delete_subscription("nonexistent")


def test_update_nonexistent_raises_not_found(store: SqliteStore) -> None:
    with pytest.raises(NotFoundError):
        store.update_subscription("nonexistent", active=False)

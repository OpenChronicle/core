"""Tests for WebhookService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from openchronicle.core.application.services.webhook_service import WebhookService
from openchronicle.core.domain.exceptions import NotFoundError
from openchronicle.core.domain.exceptions import ValidationError as DomainValidationError
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


def test_register_creates_subscription(service: WebhookService) -> None:
    sub = service.register("proj-1", "https://example.com/hook", "llm.*", "LLM events")
    assert sub.id
    assert sub.project_id == "proj-1"
    assert sub.url == "https://example.com/hook"
    assert sub.event_filter == "llm.*"
    assert sub.description == "LLM events"
    assert len(sub.secret) == 64  # 32 bytes hex


def test_register_validates_url(service: WebhookService) -> None:
    with pytest.raises(DomainValidationError, match="Invalid webhook URL"):
        service.register("proj-1", "not-a-url")


def test_register_validates_empty_url(service: WebhookService) -> None:
    with pytest.raises(DomainValidationError, match="Invalid webhook URL"):
        service.register("proj-1", "")


def test_register_validates_event_filter(service: WebhookService) -> None:
    with pytest.raises(DomainValidationError, match="Event filter must not be empty"):
        service.register("proj-1", "https://example.com/hook", "")


def test_delete_removes_subscription(service: WebhookService, store: SqliteStore) -> None:
    sub = service.register("proj-1", "https://example.com/hook")
    service.delete(sub.id)
    assert store.get_subscription(sub.id) is None


def test_delete_nonexistent_raises_not_found(service: WebhookService) -> None:
    with pytest.raises(NotFoundError):
        service.delete("nonexistent")


def test_list_returns_all(service: WebhookService) -> None:
    service.register("proj-1", "https://example.com/a")
    service.register("proj-1", "https://example.com/b")
    assert len(service.list()) == 2


def test_list_filtered(service: WebhookService) -> None:
    service.register("proj-1", "https://example.com/hook")
    assert len(service.list(project_id="proj-1")) == 1
    assert len(service.list(project_id="other")) == 0


def test_get_returns_subscription(service: WebhookService) -> None:
    sub = service.register("proj-1", "https://example.com/hook")
    got = service.get(sub.id)
    assert got.id == sub.id


def test_get_nonexistent_raises_not_found(service: WebhookService) -> None:
    with pytest.raises(NotFoundError):
        service.get("nonexistent")


def test_update_toggles_active(service: WebhookService) -> None:
    sub = service.register("proj-1", "https://example.com/hook")
    service.update(sub.id, active=False)
    got = service.get(sub.id)
    assert got.active is False


def test_sign_payload_produces_correct_hmac() -> None:
    sig = WebhookService.sign_payload("mysecret", b'{"test": true}')
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex digest


def test_sign_payload_is_deterministic() -> None:
    s1 = WebhookService.sign_payload("key", b"data")
    s2 = WebhookService.sign_payload("key", b"data")
    assert s1 == s2


def test_matches_filter_exact() -> None:
    assert WebhookService.matches_filter("llm.requested", "llm.requested") is True


def test_matches_filter_glob() -> None:
    assert WebhookService.matches_filter("llm.requested", "llm.*") is True
    assert WebhookService.matches_filter("task.completed", "llm.*") is False


def test_matches_filter_wildcard() -> None:
    assert WebhookService.matches_filter("anything", "*") is True


def test_deliver_success(service: WebhookService) -> None:
    sub = service.register("proj-1", "https://example.com/hook")
    event = Event(project_id="proj-1", type="llm.requested", payload={"model": "gpt-4"})

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("openchronicle.core.application.services.webhook_service.httpx.post", return_value=mock_resp):
        attempt = service.deliver(sub, event)

    assert attempt.success is True
    assert attempt.status_code == 200
    assert attempt.error_message is None


def test_deliver_failure_records_error(service: WebhookService) -> None:
    sub = service.register("proj-1", "https://example.com/hook")
    event = Event(project_id="proj-1", type="llm.requested", payload={})

    with patch(
        "openchronicle.core.application.services.webhook_service.httpx.post",
        side_effect=Exception("connection refused"),
    ):
        attempt = service.deliver(sub, event)

    assert attempt.success is False
    assert attempt.status_code is None
    assert "connection refused" in (attempt.error_message or "")

"""Tests for webhook API routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openchronicle.core.domain.models.project import Project
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore
from openchronicle.interfaces.api.app import create_app
from openchronicle.interfaces.api.config import HTTPConfig


@pytest.fixture()
def container(tmp_path: object) -> object:
    """Lightweight container mock using real store + webhook service."""
    from openchronicle.core.application.services.webhook_service import WebhookService
    from openchronicle.core.infrastructure.logging.event_logger import EventLogger

    store = SqliteStore(db_path=":memory:")
    store.init_schema()
    store.add_project(Project(id="proj-1", name="Test"))

    class FakeContainer:
        def __init__(self) -> None:
            self.storage = store
            self.event_logger = EventLogger(store)
            self.webhook_service = WebhookService(store=store)
            self.webhook_dispatcher = None

        def emit_event(self, event: object) -> None:
            self.event_logger.append(event)  # type: ignore[arg-type]

        def ensure_webhook_dispatcher(self) -> None:
            pass

    return FakeContainer()


@pytest.fixture()
def client(container: object) -> TestClient:
    config = HTTPConfig()
    app = create_app(container, config)  # type: ignore[arg-type]
    return TestClient(app)


def test_register_returns_201(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/webhook",
        json={"project_id": "proj-1", "url": "https://example.com/hook", "event_filter": "llm.*"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/hook"
    assert data["event_filter"] == "llm.*"
    assert "***" in data["secret"]  # Masked


def test_list_returns_subscriptions(client: TestClient) -> None:
    client.post("/api/v1/webhook", json={"project_id": "proj-1", "url": "https://example.com/a"})
    client.post("/api/v1/webhook", json={"project_id": "proj-1", "url": "https://example.com/b"})
    resp = client.get("/api/v1/webhook")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_returns_single(client: TestClient) -> None:
    create_resp = client.post("/api/v1/webhook", json={"project_id": "proj-1", "url": "https://example.com/hook"})
    webhook_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/webhook/{webhook_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == webhook_id


def test_delete_returns_204(client: TestClient) -> None:
    create_resp = client.post("/api/v1/webhook", json={"project_id": "proj-1", "url": "https://example.com/hook"})
    webhook_id = create_resp.json()["id"]
    resp = client.delete(f"/api/v1/webhook/{webhook_id}")
    assert resp.status_code == 204


def test_deliveries_returns_attempts(client: TestClient, container: object) -> None:
    create_resp = client.post("/api/v1/webhook", json={"project_id": "proj-1", "url": "https://example.com/hook"})
    webhook_id = create_resp.json()["id"]

    # Add a delivery directly
    from openchronicle.core.domain.models.webhook import DeliveryAttempt

    container.storage.add_delivery(  # type: ignore[attr-defined]
        DeliveryAttempt(subscription_id=webhook_id, event_id="evt-1", success=True, status_code=200)
    )

    resp = client.get(f"/api/v1/webhook/{webhook_id}/deliveries")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_register_validates_url(client: TestClient) -> None:
    resp = client.post("/api/v1/webhook", json={"project_id": "proj-1", "url": "not-a-url"})
    assert resp.status_code == 422


def test_delete_nonexistent_returns_404(client: TestClient) -> None:
    resp = client.delete("/api/v1/webhook/nonexistent")
    assert resp.status_code == 404


def test_path_validation_on_webhook_id(client: TestClient) -> None:
    resp = client.get("/api/v1/webhook/ ")
    # FastAPI should reject empty/whitespace-only path params
    assert resp.status_code in (404, 422)

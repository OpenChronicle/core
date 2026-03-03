"""Tests for the generic inbound hooks API endpoint."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from openchronicle.core.domain.models.project import Project, Task, TaskStatus
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore
from openchronicle.interfaces.api.app import create_app
from openchronicle.interfaces.api.config import HTTPConfig


def _make_task(project_id: str = "proj-1") -> Task:
    return Task(
        id="task-abc",
        project_id=project_id,
        type="plugin.invoke",
        payload={"handler": "test.hook", "input": {"webhook_payload": {}}},
        status=TaskStatus.PENDING,
    )


@pytest.fixture()
def container() -> object:
    """Minimal container mock with orchestrator + handler_registry."""
    store = SqliteStore(db_path=":memory:")
    store.init_schema()
    store.add_project(Project(id="proj-1", name="Test"))

    # Real-enough handler registry with one handler
    mock_handler = AsyncMock(return_value={"ok": True})
    registry = MagicMock()
    registry.get = MagicMock(side_effect=lambda name: mock_handler if name == "test.hook" else None)

    mock_orchestrator = MagicMock()
    mock_orchestrator.handler_registry = registry
    mock_orchestrator.submit_task = MagicMock(return_value=_make_task())
    mock_orchestrator.execute_task = AsyncMock(return_value={"ok": True})

    class FakeContainer:
        def __init__(self) -> None:
            self.storage = store
            self.orchestrator = mock_orchestrator

    return FakeContainer()


@pytest.fixture()
def client(container: object) -> TestClient:
    config = HTTPConfig()
    app = create_app(container, config)  # type: ignore[arg-type]
    return TestClient(app)


def test_json_body_dispatches(client: TestClient, container: Any) -> None:
    """JSON POST dispatches via task_submit and returns 202."""
    resp = client.post(
        "/api/v1/hooks/test.hook?project_id=proj-1",
        json={"event": "media.play", "data": "test"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "task_id" in data
    assert data["task_id"] == "task-abc"


def test_multipart_payload_field_parsed(client: TestClient) -> None:
    """Multipart form-data with a ``payload`` JSON field is parsed."""
    payload_json = json.dumps({"event": "media.scrobble", "Metadata": {"title": "Test"}})
    # Send as actual multipart form data
    resp = client.post(
        "/api/v1/hooks/test.hook?project_id=proj-1",
        data={"payload": payload_json},
    )
    assert resp.status_code == 202


def test_unknown_handler_returns_404(client: TestClient) -> None:
    """POST to an unknown handler returns 404."""
    resp = client.post(
        "/api/v1/hooks/no.such.handler?project_id=proj-1",
        json={"event": "test"},
    )
    assert resp.status_code == 404
    assert "Unknown handler" in resp.json()["detail"]


def test_missing_project_id_returns_422(client: TestClient) -> None:
    """POST without project_id query param returns 422."""
    resp = client.post(
        "/api/v1/hooks/test.hook",
        json={"event": "test"},
    )
    assert resp.status_code == 422


def test_successful_dispatch_returns_task_id(client: TestClient, container: Any) -> None:
    """Verify the orchestrator.submit_task is called with correct args."""
    resp = client.post(
        "/api/v1/hooks/test.hook?project_id=proj-1",
        json={"key": "value"},
    )
    assert resp.status_code == 202
    assert resp.json()["task_id"] == "task-abc"

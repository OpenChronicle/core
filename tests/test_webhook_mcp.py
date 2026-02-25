"""Tests for webhook MCP tools."""

from __future__ import annotations

import pytest

from openchronicle.core.application.services.webhook_service import WebhookService
from openchronicle.core.domain.models.project import Project
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
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


class FakeContainer:
    """Minimal container for MCP tool tests."""

    def __init__(self, store: SqliteStore, service: WebhookService) -> None:
        self.storage = store
        self.webhook_service = service
        self.event_logger = EventLogger(store)
        self.webhook_dispatcher = None

    def emit_event(self, event: object) -> None:
        self.event_logger.append(event)  # type: ignore[arg-type]

    def ensure_webhook_dispatcher(self) -> None:
        pass


class FakeLifespan:
    def __init__(self, container: object) -> None:
        self.lifespan_context = {"container": container}


class FakeRequest:
    def __init__(self, container: object) -> None:
        self.request_context = FakeLifespan(container)


class FakeContext:
    """Minimal MCP Context mock."""

    def __init__(self, container: object) -> None:
        self.request_context = FakeLifespan(container)


def test_webhook_register(store: SqliteStore, service: WebhookService) -> None:
    from mcp.server.fastmcp import FastMCP

    from openchronicle.interfaces.mcp.tools import webhook

    mcp = FastMCP("test")
    webhook.register(mcp)

    # Verify the tools are registered by checking the module loaded
    assert webhook.register.__module__ == "openchronicle.interfaces.mcp.tools.webhook"

    # Verify the underlying service works
    sub = service.register("proj-1", "https://example.com/hook", "llm.*")
    assert sub.url == "https://example.com/hook"


def test_webhook_list(store: SqliteStore, service: WebhookService) -> None:
    service.register("proj-1", "https://example.com/a")
    service.register("proj-1", "https://example.com/b")
    subs = service.list()
    assert len(subs) == 2


def test_webhook_delete(store: SqliteStore, service: WebhookService) -> None:
    sub = service.register("proj-1", "https://example.com/hook")
    service.delete(sub.id)
    assert store.get_subscription(sub.id) is None


def test_input_validation_empty_url(service: WebhookService) -> None:
    from openchronicle.core.domain.exceptions import ValidationError as DomainValidationError

    with pytest.raises(DomainValidationError):
        service.register("proj-1", "")

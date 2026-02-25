"""Tests for webhook domain models and port."""

from __future__ import annotations

import fnmatch

import pytest

from openchronicle.core.domain.models.webhook import DeliveryAttempt, WebhookSubscription
from openchronicle.core.domain.ports.webhook_store_port import WebhookStorePort


def test_webhook_subscription_creation() -> None:
    sub = WebhookSubscription(
        project_id="proj-1",
        url="https://example.com/hook",
        secret="s3cret",
        event_filter="llm.*",
        description="LLM events",
    )
    assert sub.id  # UUID generated
    assert sub.project_id == "proj-1"
    assert sub.url == "https://example.com/hook"
    assert sub.secret == "s3cret"
    assert sub.event_filter == "llm.*"
    assert sub.active is True
    assert sub.description == "LLM events"
    assert sub.created_at is not None


def test_delivery_attempt_creation() -> None:
    attempt = DeliveryAttempt(
        subscription_id="sub-1",
        event_id="evt-1",
        status_code=200,
        success=True,
        attempt_number=1,
    )
    assert attempt.id  # UUID generated
    assert attempt.subscription_id == "sub-1"
    assert attempt.event_id == "evt-1"
    assert attempt.status_code == 200
    assert attempt.success is True
    assert attempt.attempt_number == 1
    assert attempt.error_message is None
    assert attempt.delivered_at is not None


def test_webhook_store_port_is_abstract() -> None:
    with pytest.raises(TypeError):
        WebhookStorePort()  # type: ignore[abstract]


@pytest.mark.parametrize(
    "event_type,filter_pattern,expected",
    [
        ("llm.requested", "llm.*", True),
        ("llm.completed", "llm.*", True),
        ("task.completed", "llm.*", False),
        ("task.completed", "*", True),
        ("task.completed", "task.completed", True),
        ("webhook.registered", "webhook.*", True),
        ("llm.requested", "llm.requested", True),
        ("llm.requested", "*.requested", True),
    ],
)
def test_event_filter_glob_matching(event_type: str, filter_pattern: str, expected: bool) -> None:
    """Verify fnmatch glob semantics work for event filter patterns."""
    assert fnmatch.fnmatch(event_type, filter_pattern) is expected

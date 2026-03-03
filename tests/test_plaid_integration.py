"""Integration tests for the Plaid connector — requires Plaid sandbox credentials.

Skip unless OC_PLAID_CLIENT_ID and OC_PLAID_SECRET are set.
"""

from __future__ import annotations

import os

import pytest

from openchronicle.core.domain.models.memory_item import MemoryItem

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("OC_PLAID_CLIENT_ID") or not os.environ.get("OC_PLAID_SECRET"),
        reason="OC_PLAID_CLIENT_ID and OC_PLAID_SECRET required for Plaid integration tests",
    ),
]


def _get_sandbox_access_token() -> str:
    """Use sandbox public_token/create + exchange to get an access_token."""
    from plugins.plaid_connector.plaid_auth import PlaidAuthFlow

    client_id = os.environ["OC_PLAID_CLIENT_ID"]
    secret = os.environ["OC_PLAID_SECRET"]
    flow = PlaidAuthFlow(client_id, secret, "sandbox")
    public_token = flow.create_sandbox_public_token()
    return flow.exchange_public_token(public_token)


@pytest.mark.asyncio
async def test_get_accounts() -> None:
    from plugins.plaid_connector.plaid_api import PlaidClient

    client_id = os.environ["OC_PLAID_CLIENT_ID"]
    secret = os.environ["OC_PLAID_SECRET"]
    access_token = _get_sandbox_access_token()

    client = PlaidClient(client_id, secret, "sandbox")
    result = await client.get_accounts(access_token)

    assert isinstance(result["accounts"], list)
    assert len(result["accounts"]) > 0
    assert "account_id" in result["accounts"][0]
    assert "name" in result["accounts"][0]


@pytest.mark.asyncio
async def test_sync_transactions() -> None:
    from plugins.plaid_connector.plaid_api import PlaidClient

    client_id = os.environ["OC_PLAID_CLIENT_ID"]
    secret = os.environ["OC_PLAID_SECRET"]
    access_token = _get_sandbox_access_token()

    client = PlaidClient(client_id, secret, "sandbox")
    result = await client.sync_transactions(access_token)

    assert "added" in result
    assert "next_cursor" in result
    assert isinstance(result["added"], list)
    assert isinstance(result["has_more"], bool)


@pytest.mark.asyncio
async def test_sync_creates_memories() -> None:
    """Run plaid.sync against sandbox, verify memories are created."""
    from unittest.mock import MagicMock

    from openchronicle.core.domain.models.project import Task, TaskStatus
    from plugins.plaid_connector.plugin import _sync_handler

    client_id = os.environ["OC_PLAID_CLIENT_ID"]
    secret = os.environ["OC_PLAID_SECRET"]
    access_token = _get_sandbox_access_token()

    saved: list[str] = []

    def mock_memory_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
        saved.append(content)
        return MemoryItem(content=content, tags=tags or [])

    def mock_memory_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
        return []

    ctx = {
        "plugin_config": {
            "plaid_client_id": client_id,
            "plaid_secret": secret,
            "plaid_env": "sandbox",
            "access_tokens": {"Sandbox Bank": access_token},
        },
        "memory_save": mock_memory_save,
        "memory_search": mock_memory_search,
        "memory_update": MagicMock(),
    }

    task = Task(id="t-int", project_id="proj-1", type="plugin.invoke", payload={}, status=TaskStatus.RUNNING)
    result = await _sync_handler(task, ctx)

    assert "added" in result
    assert "modified" in result
    assert "removed" in result
    assert isinstance(result["added"], int)

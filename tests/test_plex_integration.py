"""Integration tests for the Plex connector — requires a real Plex server.

Skip unless OC_PLEX_URL and OC_PLEX_TOKEN are set.
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("OC_PLEX_URL") or not os.environ.get("OC_PLEX_TOKEN"),
        reason="OC_PLEX_URL and OC_PLEX_TOKEN required for Plex integration tests",
    ),
]


@pytest.mark.asyncio
async def test_get_libraries() -> None:
    from plugins.plex_connector.plex_api import PlexClient

    url = os.environ["OC_PLEX_URL"]
    token = os.environ["OC_PLEX_TOKEN"]
    client = PlexClient(url, token)
    libs = await client.get_libraries()
    assert isinstance(libs, list)
    if libs:
        assert "key" in libs[0]
        assert "title" in libs[0]


@pytest.mark.asyncio
async def test_get_watch_history() -> None:
    from plugins.plex_connector.plex_api import PlexClient

    url = os.environ["OC_PLEX_URL"]
    token = os.environ["OC_PLEX_TOKEN"]
    client = PlexClient(url, token)
    history = await client.get_watch_history()
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_sync_creates_memories() -> None:
    """Run plex.sync against a real server, verify memories are created."""
    from unittest.mock import MagicMock

    from openchronicle.core.domain.models.memory_item import MemoryItem
    from openchronicle.core.domain.models.project import Task, TaskStatus
    from plugins.plex_connector.plugin import _sync_handler

    saved: list[str] = []

    def mock_memory_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
        saved.append(content)
        return MemoryItem(content=content, tags=tags or [])

    def mock_memory_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
        return []

    ctx = {
        "plugin_config": {
            "plex_url": os.environ["OC_PLEX_URL"],
            "plex_token": os.environ["OC_PLEX_TOKEN"],
            "sync_history_days": 7,
        },
        "memory_save": mock_memory_save,
        "memory_search": mock_memory_search,
        "memory_update": MagicMock(),
    }

    task = Task(id="t-int", project_id="proj-1", type="plugin.invoke", payload={}, status=TaskStatus.RUNNING)
    result = await _sync_handler(task, ctx)

    assert "synced" in result
    assert "watch_history" in result
    assert isinstance(result["synced"], int)

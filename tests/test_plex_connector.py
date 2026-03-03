"""Unit tests for the Plex connector plugin (mocked httpx)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from openchronicle.core.domain.models.memory_item import MemoryItem
from openchronicle.core.domain.models.project import Task, TaskStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _plex_response(metadata: list[dict[str, Any]] | None = None, *, key: str = "Metadata") -> dict[str, Any]:
    """Build a Plex-style MediaContainer response."""
    container: dict[str, Any] = {}
    if metadata is not None:
        container[key] = metadata
    return {"MediaContainer": container}


def _plex_sections_response(dirs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"MediaContainer": {"Directory": dirs}}


def _make_task(payload: dict[str, Any] | None = None) -> Task:
    return Task(
        id="t-1",
        project_id="proj-1",
        type="plugin.invoke",
        payload=payload or {},
        status=TaskStatus.RUNNING,
    )


def _make_memory_item(content: str, item_id: str = "mem-1", tags: list[str] | None = None) -> MemoryItem:
    return MemoryItem(id=item_id, content=content, tags=tags or [])


# ---------------------------------------------------------------------------
# plex_api tests
# ---------------------------------------------------------------------------


class TestPlexClientGetLibraries:
    @pytest.mark.asyncio
    async def test_parses_sections_response(self) -> None:
        from plugins.plex_connector.plex_api import PlexClient

        resp_data = _plex_sections_response(
            [
                {"key": "1", "title": "Movies", "type": "movie"},
                {"key": "2", "title": "TV Shows", "type": "show"},
            ]
        )
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = resp_data
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            client = PlexClient("http://localhost:32400", "test-token")
            libs = await client.get_libraries()

        assert len(libs) == 2
        assert libs[0] == {"key": "1", "title": "Movies", "type": "movie"}
        assert libs[1] == {"key": "2", "title": "TV Shows", "type": "show"}


class TestPlexClientGetItemsSince:
    @pytest.mark.asyncio
    async def test_handles_pagination(self) -> None:
        """Two pages of results, second page smaller than page_size."""
        from plugins.plex_connector.plex_api import PlexClient

        page1 = _plex_response([{"title": f"Item {i}"} for i in range(2)])
        page2 = _plex_response([{"title": "Item 2"}])

        responses = [
            MagicMock(spec=httpx.Response, **{"json.return_value": page1, "raise_for_status": MagicMock()}),
            MagicMock(spec=httpx.Response, **{"json.return_value": page2, "raise_for_status": MagicMock()}),
        ]
        call_count = 0

        async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            return resp

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            client = PlexClient("http://localhost:32400", "test-token")
            items = await client.get_items_since("1", 0, page_size=2)

        assert len(items) == 3
        assert call_count == 2


class TestPlexClientGetWatchHistory:
    @pytest.mark.asyncio
    async def test_parses_history_response(self) -> None:
        from plugins.plex_connector.plex_api import PlexClient

        resp_data = _plex_response(
            [
                {"title": "Inception", "type": "movie", "viewedAt": 1709337600, "ratingKey": "100"},
            ]
        )
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = resp_data
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            client = PlexClient("http://localhost:32400", "test-token")
            history = await client.get_watch_history()

        assert len(history) == 1
        assert history[0]["title"] == "Inception"
        assert history[0]["ratingKey"] == "100"


class TestPlexClientEmptyMetadata:
    @pytest.mark.asyncio
    async def test_empty_metadata_returns_empty_list(self) -> None:
        from plugins.plex_connector.plex_api import PlexClient

        resp_data = _plex_response()  # No Metadata key
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = resp_data
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            client = PlexClient("http://localhost:32400", "test-token")
            history = await client.get_watch_history()

        assert history == []


# ---------------------------------------------------------------------------
# plex.sync handler tests
# ---------------------------------------------------------------------------


class TestSyncHandler:
    @pytest.mark.asyncio
    async def test_full_sync_round_trip(self) -> None:
        """Mock client returns items; verify memory_save calls."""
        from plugins.plex_connector.plugin import _sync_handler

        saved: list[tuple[str, list[str]]] = []

        def mock_memory_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
            saved.append((content, tags or []))
            return _make_memory_item(content, tags=tags)

        def mock_memory_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            return []  # No prior watermark

        ctx: dict[str, Any] = {
            "plugin_config": {
                "plex_url": "http://localhost:32400",
                "plex_token": "real-token",
                "sync_libraries": [],
                "sync_history_days": 7,
            },
            "memory_save": mock_memory_save,
            "memory_search": mock_memory_search,
            "memory_update": MagicMock(),
        }

        with patch("plugins.plex_connector.plugin.PlexClient") as MockClient:
            instance = AsyncMock()
            instance.get_libraries.return_value = [
                {"key": "1", "title": "Movies", "type": "movie"},
            ]
            instance.get_items_since.return_value = [
                {"title": "Inception", "type": "movie", "year": 2010, "addedAt": 9999999999},
            ]
            instance.get_watch_history.return_value = [
                {"title": "Inception", "type": "movie", "viewedAt": 9999999999, "ratingKey": "1"},
            ]
            MockClient.return_value = instance

            task = _make_task()
            result = await _sync_handler(task, ctx)

        assert result["synced"] == 1
        assert result["watch_history"] == 1
        # 1 item + 1 watch + 1 watermark = 3 saves
        assert len(saved) == 3
        assert any("[Plex]" in s[0] for s in saved)
        assert any("[Plex Watch]" in s[0] for s in saved)
        assert any("[Plex Sync State]" in s[0] for s in saved)

    @pytest.mark.asyncio
    async def test_incremental_sync_uses_watermark(self) -> None:
        """Pre-seed watermark memory; verify only new items synced."""
        from plugins.plex_connector.plugin import _sync_handler

        saved: list[str] = []
        watermark_dt = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        watermark_ts = int(watermark_dt.timestamp())

        def mock_memory_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
            saved.append(content)
            return _make_memory_item(content)

        def mock_memory_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            if tags and "plex-sync-state" in tags:
                return [
                    _make_memory_item(
                        f"[Plex Sync State] last_sync: {watermark_dt.isoformat()} | items: 10 | watches: 5",
                        item_id="wm-1",
                    )
                ]
            return []

        ctx: dict[str, Any] = {
            "plugin_config": {
                "plex_url": "http://localhost:32400",
                "plex_token": "real-token",
            },
            "memory_save": mock_memory_save,
            "memory_search": mock_memory_search,
            "memory_update": MagicMock(),
        }

        with patch("plugins.plex_connector.plugin.PlexClient") as MockClient:
            instance = AsyncMock()
            instance.get_libraries.return_value = [{"key": "1", "title": "Movies", "type": "movie"}]
            instance.get_items_since.return_value = []
            instance.get_watch_history.return_value = []
            MockClient.return_value = instance

            task = _make_task()
            result = await _sync_handler(task, ctx)

            # Verify get_items_since was called with watermark timestamp
            instance.get_items_since.assert_called_once_with("1", watermark_ts)

        assert result["synced"] == 0
        assert result["watch_history"] == 0

    @pytest.mark.asyncio
    async def test_missing_config_raises_error(self) -> None:
        from plugins.plex_connector.plugin import _sync_handler

        ctx: dict[str, Any] = {"plugin_config": {}}
        task = _make_task()

        with pytest.raises(ValueError, match="plex_url and plex_token"):
            await _sync_handler(task, ctx)

    @pytest.mark.asyncio
    async def test_empty_library_returns_zeros(self) -> None:
        from plugins.plex_connector.plugin import _sync_handler

        ctx: dict[str, Any] = {
            "plugin_config": {
                "plex_url": "http://localhost:32400",
                "plex_token": "real-token",
            },
            "memory_save": MagicMock(return_value=_make_memory_item("")),
            "memory_search": MagicMock(return_value=[]),
            "memory_update": MagicMock(),
        }

        with patch("plugins.plex_connector.plugin.PlexClient") as MockClient:
            instance = AsyncMock()
            instance.get_libraries.return_value = []
            instance.get_watch_history.return_value = []
            MockClient.return_value = instance

            result = await _sync_handler(_make_task(), ctx)

        assert result == {"synced": 0, "watch_history": 0}


# ---------------------------------------------------------------------------
# plex.webhook handler tests
# ---------------------------------------------------------------------------


class TestWebhookHandler:
    @pytest.mark.asyncio
    async def test_scrobble_saves_watch_memory(self) -> None:
        from plugins.plex_connector.plugin import _webhook_handler

        saved: list[str] = []

        def mock_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
            saved.append(content)
            return _make_memory_item(content)

        task = _make_task(
            payload={
                "webhook_payload": {
                    "event": "media.scrobble",
                    "Metadata": {"title": "Breaking Bad S05E16", "type": "episode"},
                },
            }
        )
        ctx: dict[str, Any] = {"memory_save": mock_save}
        result = await _webhook_handler(task, ctx)

        assert result["saved"] is True
        assert result["event"] == "media.scrobble"
        assert len(saved) == 1
        assert "[Plex Watch]" in saved[0]
        assert "Breaking Bad" in saved[0]

    @pytest.mark.asyncio
    async def test_library_new_saves_item_memory(self) -> None:
        from plugins.plex_connector.plugin import _webhook_handler

        saved: list[str] = []

        def mock_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
            saved.append(content)
            return _make_memory_item(content)

        task = _make_task(
            payload={
                "webhook_payload": {
                    "event": "library.new",
                    "Metadata": {
                        "title": "Dune: Part Two",
                        "type": "movie",
                        "year": 2024,
                        "librarySectionTitle": "Movies",
                    },
                },
            }
        )
        ctx: dict[str, Any] = {"memory_save": mock_save}
        result = await _webhook_handler(task, ctx)

        assert result["saved"] is True
        assert result["event"] == "library.new"
        assert len(saved) == 1
        assert "[Plex]" in saved[0]
        assert "Dune" in saved[0]

    @pytest.mark.asyncio
    async def test_pause_event_is_ignored(self) -> None:
        from plugins.plex_connector.plugin import _webhook_handler

        task = _make_task(
            payload={
                "webhook_payload": {"event": "media.pause", "Metadata": {"title": "Test"}},
            }
        )
        result = await _webhook_handler(task, {})

        assert result["ignored"] is True
        assert result["event"] == "media.pause"


# ---------------------------------------------------------------------------
# plex.query handler tests
# ---------------------------------------------------------------------------


class TestQueryHandler:
    @pytest.mark.asyncio
    async def test_basic_search_returns_results(self) -> None:
        from plugins.plex_connector.plugin import _query_handler

        def mock_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            return [_make_memory_item("[Plex] Title: Inception | Type: movie", tags=["plex-item"])]

        task = _make_task(payload={"query": "Inception"})
        ctx: dict[str, Any] = {"memory_search": mock_search}
        result = await _query_handler(task, ctx)

        assert len(result["results"]) == 1
        assert "Inception" in result["results"][0]["content"]
        assert result["summary"] is None

    @pytest.mark.asyncio
    async def test_summarize_calls_llm_complete(self) -> None:
        from plugins.plex_connector.plugin import _query_handler

        def mock_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            return [_make_memory_item("[Plex] Title: Inception | Type: movie", tags=["plex-item"])]

        @dataclass
        class FakeLLMResponse:
            content: str = "Inception is a 2010 sci-fi film."

        mock_llm = AsyncMock(return_value=FakeLLMResponse())

        task = _make_task(payload={"query": "Tell me about Inception", "summarize": True})
        ctx: dict[str, Any] = {"memory_search": mock_search, "llm_complete": mock_llm}
        result = await _query_handler(task, ctx)

        assert result["summary"] is not None
        assert "Inception" in result["summary"]
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_results_returns_empty(self) -> None:
        from plugins.plex_connector.plugin import _query_handler

        def mock_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            return []

        task = _make_task(payload={"query": "nonexistent"})
        ctx: dict[str, Any] = {"memory_search": mock_search}
        result = await _query_handler(task, ctx)

        assert result["results"] == []
        assert result["summary"] is None

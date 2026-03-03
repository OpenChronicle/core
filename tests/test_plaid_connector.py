"""Unit tests for the Plaid connector plugin handlers (mocked context closures)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openchronicle.core.domain.models.memory_item import MemoryItem
from openchronicle.core.domain.models.project import Task, TaskStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _base_config() -> dict[str, Any]:
    return {
        "plaid_client_id": "test-cid",
        "plaid_secret": "test-sec",
        "plaid_env": "sandbox",
        "access_tokens": {"Chase": "access-tok-chase"},
    }


def _txn(
    *,
    txn_id: str = "txn_1",
    name: str = "Starbucks",
    amount: float = 4.50,
    date: str = "2026-03-01",
    category: str = "FOOD_AND_DRINK",
    account_id: str = "acc_1",
    pending: bool = False,
) -> dict[str, Any]:
    return {
        "transaction_id": txn_id,
        "name": name,
        "amount": amount,
        "date": date,
        "personal_finance_category": {"primary": category},
        "account_id": account_id,
        "pending": pending,
    }


# ---------------------------------------------------------------------------
# plaid.sync handler tests
# ---------------------------------------------------------------------------


class TestSyncHandler:
    @pytest.mark.asyncio
    async def test_full_round_trip(self) -> None:
        """Mock client returns transactions; verify memory_save calls."""
        from plugins.plaid_connector.plugin import _sync_handler

        saved: list[tuple[str, list[str]]] = []

        def mock_memory_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
            saved.append((content, tags or []))
            return _make_memory_item(content, tags=tags)

        def mock_memory_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            return []

        ctx: dict[str, Any] = {
            "plugin_config": _base_config(),
            "memory_save": mock_memory_save,
            "memory_search": mock_memory_search,
            "memory_update": MagicMock(),
        }

        with patch("plugins.plaid_connector.plugin.PlaidClient") as MockClient:
            instance = AsyncMock()
            instance.get_accounts.return_value = {
                "accounts": [{"account_id": "acc_1", "name": "Checking", "mask": "0123"}],
                "item": {},
            }
            instance.sync_transactions.return_value = {
                "added": [_txn()],
                "modified": [],
                "removed": [],
                "next_cursor": "cur_1",
                "has_more": False,
                "accounts": [],
            }
            MockClient.return_value = instance

            result = await _sync_handler(_make_task(), ctx)

        assert result["added"] == 1
        assert result["modified"] == 0
        assert result["removed"] == 0

        # 1 transaction + 1 sync state = 2 saves
        assert len(saved) == 2
        assert any("[Transaction]" in s[0] for s in saved)
        assert any("food-and-drink" in s[1] for s in saved)

    @pytest.mark.asyncio
    async def test_incremental_with_cursor(self) -> None:
        """Pre-existing cursor is passed to sync_transactions."""
        import json

        from plugins.plaid_connector.plugin import _sync_handler

        sync_state = json.dumps({"cursors": {"Chase": "prev_cursor"}})

        def mock_memory_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            if tags and "plaid-sync-state" in tags:
                return [_make_memory_item(sync_state, item_id="ss-1")]
            return []

        ctx: dict[str, Any] = {
            "plugin_config": _base_config(),
            "memory_save": MagicMock(return_value=_make_memory_item("")),
            "memory_search": mock_memory_search,
            "memory_update": MagicMock(),
        }

        with patch("plugins.plaid_connector.plugin.PlaidClient") as MockClient:
            instance = AsyncMock()
            instance.get_accounts.return_value = {"accounts": [], "item": {}}
            instance.sync_transactions.return_value = {
                "added": [],
                "modified": [],
                "removed": [],
                "next_cursor": "new_cursor",
                "has_more": False,
                "accounts": [],
            }
            MockClient.return_value = instance

            await _sync_handler(_make_task(), ctx)

            # Verify the cursor was passed
            instance.sync_transactions.assert_called_once_with("access-tok-chase", cursor="prev_cursor")

    @pytest.mark.asyncio
    async def test_missing_config_raises_error(self) -> None:
        from plugins.plaid_connector.plugin import _sync_handler

        ctx: dict[str, Any] = {"plugin_config": {}}
        with pytest.raises(ValueError, match="plaid_client_id and plaid_secret"):
            await _sync_handler(_make_task(), ctx)

    @pytest.mark.asyncio
    async def test_no_access_tokens_raises_error(self) -> None:
        from plugins.plaid_connector.plugin import _sync_handler

        config = _base_config()
        config["access_tokens"] = {}
        ctx: dict[str, Any] = {"plugin_config": config}

        with pytest.raises(ValueError, match="No access_tokens"):
            await _sync_handler(_make_task(), ctx)

    @pytest.mark.asyncio
    async def test_modified_txn_updates_memory(self) -> None:
        """Modified transaction found in memory → memory_update called."""
        from plugins.plaid_connector.plugin import _sync_handler

        existing_mem = _make_memory_item(
            "[Transaction] 2026-02-28 | Starbucks | $3.50 | FOOD_AND_DRINK\n"
            "Account: Checking (****0123) | Plaid ID: txn_1\nPending: True",
            item_id="mem-existing",
            tags=["plaid-txn", "finance", "food-and-drink"],
        )

        def mock_memory_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            if "plaid-sync-state" in (tags or []):
                return []
            if "txn_1" in query:
                return [existing_mem]
            return []

        mock_update = MagicMock()

        ctx: dict[str, Any] = {
            "plugin_config": _base_config(),
            "memory_save": MagicMock(return_value=_make_memory_item("")),
            "memory_search": mock_memory_search,
            "memory_update": mock_update,
        }

        modified_txn = _txn(pending=False, amount=4.50)

        with patch("plugins.plaid_connector.plugin.PlaidClient") as MockClient:
            instance = AsyncMock()
            instance.get_accounts.return_value = {
                "accounts": [{"account_id": "acc_1", "name": "Checking", "mask": "0123"}],
                "item": {},
            }
            instance.sync_transactions.return_value = {
                "added": [],
                "modified": [modified_txn],
                "removed": [],
                "next_cursor": "cur_2",
                "has_more": False,
                "accounts": [],
            }
            MockClient.return_value = instance

            result = await _sync_handler(_make_task(), ctx)

        assert result["modified"] == 1
        # memory_update called for the modified txn (sync state uses memory_save since no prior state)
        assert mock_update.call_count == 1
        first_call_kwargs = mock_update.call_args_list[0]
        assert first_call_kwargs.args[0] == "mem-existing"

    @pytest.mark.asyncio
    async def test_removed_txn_tagged(self) -> None:
        """Removed transaction → memory_update with ['plaid-txn', 'removed'] tags."""
        from plugins.plaid_connector.plugin import _sync_handler

        existing_mem = _make_memory_item(
            "[Transaction] 2026-02-28 | Starbucks | $3.50 | FOOD_AND_DRINK\n"
            "Account: Checking | Plaid ID: txn_rem\nPending: False",
            item_id="mem-rem",
            tags=["plaid-txn", "finance"],
        )

        def mock_memory_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            if "plaid-sync-state" in (tags or []):
                return []
            if "txn_rem" in query:
                return [existing_mem]
            return []

        mock_update = MagicMock()

        ctx: dict[str, Any] = {
            "plugin_config": _base_config(),
            "memory_save": MagicMock(return_value=_make_memory_item("")),
            "memory_search": mock_memory_search,
            "memory_update": mock_update,
        }

        with patch("plugins.plaid_connector.plugin.PlaidClient") as MockClient:
            instance = AsyncMock()
            instance.get_accounts.return_value = {"accounts": [], "item": {}}
            instance.sync_transactions.return_value = {
                "added": [],
                "modified": [],
                "removed": [{"transaction_id": "txn_rem"}],
                "next_cursor": "cur_3",
                "has_more": False,
                "accounts": [],
            }
            MockClient.return_value = instance

            result = await _sync_handler(_make_task(), ctx)

        assert result["removed"] == 1
        # memory_update called for the removed txn (sync state uses memory_save since no prior state)
        assert mock_update.call_count == 1
        first_call = mock_update.call_args_list[0]
        assert first_call.kwargs.get("tags") == ["plaid-txn", "removed"]

    @pytest.mark.asyncio
    async def test_sync_state_updated(self) -> None:
        """After sync, sync state memory is saved/updated with cursors."""
        import json

        from plugins.plaid_connector.plugin import _sync_handler

        saved: list[tuple[str, list[str], bool]] = []

        def mock_memory_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
            saved.append((content, tags or [], pinned))
            return _make_memory_item(content, tags=tags)

        ctx: dict[str, Any] = {
            "plugin_config": _base_config(),
            "memory_save": mock_memory_save,
            "memory_search": MagicMock(return_value=[]),
            "memory_update": MagicMock(),
        }

        with patch("plugins.plaid_connector.plugin.PlaidClient") as MockClient:
            instance = AsyncMock()
            instance.get_accounts.return_value = {"accounts": [], "item": {}}
            instance.sync_transactions.return_value = {
                "added": [],
                "modified": [],
                "removed": [],
                "next_cursor": "final_cursor",
                "has_more": False,
                "accounts": [],
            }
            MockClient.return_value = instance

            await _sync_handler(_make_task(), ctx)

        # Last save should be sync state
        state_saves = [(c, t, p) for c, t, p in saved if "plaid-sync-state" in t]
        assert len(state_saves) == 1
        content, tags, pinned = state_saves[0]
        state = json.loads(content)
        assert state["cursors"]["Chase"] == "final_cursor"
        assert pinned is True

    @pytest.mark.asyncio
    async def test_per_institution_cursors(self) -> None:
        """Multiple institutions each get their own cursor."""
        import json

        from plugins.plaid_connector.plugin import _sync_handler

        config = _base_config()
        config["access_tokens"] = {"Chase": "tok-chase", "Wells Fargo": "tok-wf"}

        saved: list[tuple[str, list[str]]] = []

        def mock_memory_save(content: str, tags: list[str] | None = None, pinned: bool = False) -> MemoryItem:
            saved.append((content, tags or []))
            return _make_memory_item(content, tags=tags)

        ctx: dict[str, Any] = {
            "plugin_config": config,
            "memory_save": mock_memory_save,
            "memory_search": MagicMock(return_value=[]),
            "memory_update": MagicMock(),
        }

        call_count = 0

        async def mock_sync(access_token: str, cursor: str | None = None, count: int = 100) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            cursor_val = f"cur_{call_count}"
            return {
                "added": [],
                "modified": [],
                "removed": [],
                "next_cursor": cursor_val,
                "has_more": False,
                "accounts": [],
            }

        with patch("plugins.plaid_connector.plugin.PlaidClient") as MockClient:
            instance = AsyncMock()
            instance.get_accounts.return_value = {"accounts": [], "item": {}}
            instance.sync_transactions = mock_sync
            MockClient.return_value = instance

            await _sync_handler(_make_task(), ctx)

        # Verify sync state has both institution cursors
        state_saves = [(c, t) for c, t in saved if "plaid-sync-state" in t]
        assert len(state_saves) == 1
        state = json.loads(state_saves[0][0])
        assert "Chase" in state["cursors"]
        assert "Wells Fargo" in state["cursors"]


# ---------------------------------------------------------------------------
# plaid.categorize handler tests
# ---------------------------------------------------------------------------


class TestCategorizeHandler:
    @pytest.mark.asyncio
    async def test_categorizes_uncategorized(self) -> None:
        from plugins.plaid_connector.plugin import _categorize_handler

        items = [
            _make_memory_item(
                "[Transaction] 2026-03-01 | Starbucks | $4.50 | UNCATEGORIZED\n"
                "Account: Checking | Plaid ID: txn_1\nPending: False",
                item_id="mem-1",
                tags=["plaid-txn", "finance", "uncategorized"],
            ),
        ]

        @dataclass
        class FakeLLMResponse:
            content: str = "1|FOOD_AND_DRINK"

        ctx: dict[str, Any] = {
            "memory_search": MagicMock(return_value=items),
            "memory_update": MagicMock(),
            "llm_complete": AsyncMock(return_value=FakeLLMResponse()),
        }

        result = await _categorize_handler(_make_task(), ctx)

        assert result["categorized"] == 1
        ctx["memory_update"].assert_called_once()
        call_kwargs = ctx["memory_update"].call_args
        assert call_kwargs.args[0] == "mem-1"
        assert "FOOD_AND_DRINK" in call_kwargs.kwargs["content"]
        assert "food-and-drink" in call_kwargs.kwargs["tags"]

    @pytest.mark.asyncio
    async def test_no_uncategorized_returns_zero(self) -> None:
        from plugins.plaid_connector.plugin import _categorize_handler

        ctx: dict[str, Any] = {
            "memory_search": MagicMock(return_value=[]),
            "memory_update": MagicMock(),
            "llm_complete": AsyncMock(),
        }

        result = await _categorize_handler(_make_task(), ctx)
        assert result["categorized"] == 0

    @pytest.mark.asyncio
    async def test_missing_closures_returns_error(self) -> None:
        from plugins.plaid_connector.plugin import _categorize_handler

        result = await _categorize_handler(_make_task(), {})
        assert "error" in result


# ---------------------------------------------------------------------------
# plaid.query handler tests
# ---------------------------------------------------------------------------


class TestQueryHandler:
    @pytest.mark.asyncio
    async def test_basic_search(self) -> None:
        from plugins.plaid_connector.plugin import _query_handler

        def mock_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            return [_make_memory_item("[Transaction] 2026-03-01 | Starbucks | $4.50", tags=["plaid-txn"])]

        task = _make_task(payload={"query": "Starbucks"})
        ctx: dict[str, Any] = {"memory_search": mock_search}
        result = await _query_handler(task, ctx)

        assert len(result["results"]) == 1
        assert "Starbucks" in result["results"][0]["content"]
        assert result["summary"] is None

    @pytest.mark.asyncio
    async def test_summarize_calls_llm(self) -> None:
        from plugins.plaid_connector.plugin import _query_handler

        def mock_search(query: str, tags: list[str] | None = None, top_k: int = 8) -> list[MemoryItem]:
            return [_make_memory_item("[Transaction] 2026-03-01 | Starbucks | $4.50", tags=["plaid-txn"])]

        @dataclass
        class FakeLLMResponse:
            content: str = "You spent $4.50 at Starbucks."

        mock_llm = AsyncMock(return_value=FakeLLMResponse())
        task = _make_task(payload={"query": "How much did I spend?", "summarize": True})
        ctx: dict[str, Any] = {"memory_search": mock_search, "llm_complete": mock_llm}
        result = await _query_handler(task, ctx)

        assert result["summary"] is not None
        assert "Starbucks" in result["summary"]
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self) -> None:
        from plugins.plaid_connector.plugin import _query_handler

        task = _make_task(payload={"query": ""})
        result = await _query_handler(task, {})

        assert result["results"] == []
        assert result["summary"] is None

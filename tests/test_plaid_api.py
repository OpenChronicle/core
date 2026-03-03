"""Unit tests for the Plaid API client (mocked httpx)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from plugins.plaid_connector.plaid_api import PlaidClient


def _mock_response(data: dict[str, Any]) -> MagicMock:
    """Build a mock httpx.Response returning *data* from .json()."""
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


def _patch_async_client(mock_resp: MagicMock) -> tuple[Any, AsyncMock]:
    """Context-manager patch for httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("httpx.AsyncClient", return_value=mock_client), mock_client


# ---------------------------------------------------------------------------
# sync_transactions
# ---------------------------------------------------------------------------


class TestSyncTransactions:
    @pytest.mark.asyncio
    async def test_request_body_construction(self) -> None:
        resp = _mock_response(
            {
                "added": [{"transaction_id": "txn_1"}],
                "modified": [],
                "removed": [],
                "next_cursor": "cur_abc",
                "has_more": False,
                "accounts": [{"account_id": "acc_1"}],
            }
        )
        patcher, mock_client = _patch_async_client(resp)

        with patcher:
            client = PlaidClient("cid", "sec", "sandbox")
            result = await client.sync_transactions("access-tok", cursor="prev_cur", count=50)

        # Verify request body
        call_kwargs = mock_client.post.call_args
        body = call_kwargs.kwargs["json"]
        assert body["client_id"] == "cid"
        assert body["secret"] == "sec"
        assert body["access_token"] == "access-tok"
        assert body["cursor"] == "prev_cur"
        assert body["count"] == 50

        # Verify URL
        assert call_kwargs.args[0] == "https://sandbox.plaid.com/transactions/sync"

        # Verify response normalization
        assert len(result["added"]) == 1
        assert result["next_cursor"] == "cur_abc"
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_no_cursor_omitted_from_body(self) -> None:
        resp = _mock_response({"added": [], "modified": [], "removed": [], "next_cursor": "", "has_more": False})
        patcher, mock_client = _patch_async_client(resp)

        with patcher:
            client = PlaidClient("cid", "sec")
            await client.sync_transactions("tok")

        body = mock_client.post.call_args.kwargs["json"]
        assert "cursor" not in body

    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        resp = _mock_response({})
        patcher, _ = _patch_async_client(resp)

        with patcher:
            client = PlaidClient("cid", "sec")
            result = await client.sync_transactions("tok")

        assert result["added"] == []
        assert result["modified"] == []
        assert result["removed"] == []
        assert result["next_cursor"] == ""
        assert result["has_more"] is False
        assert result["accounts"] == []


# ---------------------------------------------------------------------------
# get_accounts
# ---------------------------------------------------------------------------


class TestGetAccounts:
    @pytest.mark.asyncio
    async def test_response_parsing(self) -> None:
        resp = _mock_response(
            {
                "accounts": [
                    {"account_id": "acc_1", "name": "Checking", "mask": "0123"},
                ],
                "item": {"item_id": "item_1"},
            }
        )
        patcher, mock_client = _patch_async_client(resp)

        with patcher:
            client = PlaidClient("cid", "sec")
            result = await client.get_accounts("access-tok")

        assert len(result["accounts"]) == 1
        assert result["accounts"][0]["name"] == "Checking"
        assert result["item"]["item_id"] == "item_1"

        # Verify URL
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.args[0] == "https://sandbox.plaid.com/accounts/get"

    @pytest.mark.asyncio
    async def test_empty_accounts(self) -> None:
        resp = _mock_response({"accounts": [], "item": {}})
        patcher, _ = _patch_async_client(resp)

        with patcher:
            client = PlaidClient("cid", "sec")
            result = await client.get_accounts("tok")

        assert result["accounts"] == []
        assert result["item"] == {}


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestPlaidClientConstruction:
    def test_invalid_env_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown Plaid environment"):
            PlaidClient("cid", "sec", "staging")

    def test_production_url(self) -> None:
        client = PlaidClient("cid", "sec", "production")
        assert client._base_url == "https://production.plaid.com"

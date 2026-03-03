"""Tests for Plaid authentication flow and CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.plaid_connector.plaid_auth import PlaidAuthFlow

# ---------------------------------------------------------------------------
# PlaidAuthFlow unit tests
# ---------------------------------------------------------------------------


class TestPlaidAuthFlow:
    def setup_method(self) -> None:
        self.flow = PlaidAuthFlow("test-cid", "test-sec", "sandbox")

    @patch("plugins.plaid_connector.plaid_auth.httpx.post")
    def test_create_link_token(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"link_token": "link-sandbox-abc123"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        token = self.flow.create_link_token()

        assert token == "link-sandbox-abc123"
        mock_post.assert_called_once()
        body = mock_post.call_args.kwargs["json"]
        assert body["client_id"] == "test-cid"
        assert body["secret"] == "test-sec"
        assert body["products"] == ["transactions"]
        assert body["country_codes"] == ["US"]

    @patch("plugins.plaid_connector.plaid_auth.httpx.post")
    def test_exchange_public_token(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "access-sandbox-xyz"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        token = self.flow.exchange_public_token("public-sandbox-tok")

        assert token == "access-sandbox-xyz"
        body = mock_post.call_args.kwargs["json"]
        assert body["public_token"] == "public-sandbox-tok"
        assert body["client_id"] == "test-cid"
        assert "https://sandbox.plaid.com/item/public_token/exchange" in mock_post.call_args.args[0]

    @patch("plugins.plaid_connector.plaid_auth.httpx.post")
    def test_create_sandbox_public_token(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"public_token": "public-sandbox-auto"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        token = self.flow.create_sandbox_public_token()

        assert token == "public-sandbox-auto"
        body = mock_post.call_args.kwargs["json"]
        assert body["institution_id"] == "ins_109508"
        assert body["initial_products"] == ["transactions"]

    def test_create_sandbox_public_token_rejects_production(self) -> None:
        flow = PlaidAuthFlow("cid", "sec", "production")
        with pytest.raises(ValueError, match="only available in sandbox"):
            flow.create_sandbox_public_token()

    def test_link_url_format(self) -> None:
        url = self.flow.link_url("link-sandbox-abc123")
        assert "https://cdn.plaid.com/link/v2/stable/link.html" in url
        assert "token=link-sandbox-abc123" in url

    def test_invalid_env_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown Plaid environment"):
            PlaidAuthFlow("cid", "sec", "development")


# ---------------------------------------------------------------------------
# _cmd_plaid_auth CLI tests
# ---------------------------------------------------------------------------


class TestCmdPlaidAuth:
    @patch("plugins.plaid_connector.plaid_auth.httpx.post")
    def test_sandbox_shortcut_writes_config(
        self,
        mock_post: MagicMock,
        tmp_path: Path,
    ) -> None:
        from plugins.plaid_connector.cli import _cmd_plaid_auth

        # Setup plugin config
        plugin_dir = tmp_path / "plaid_connector"
        plugin_dir.mkdir()
        config_path = plugin_dir / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "plaid_client_id": "test-cid",
                    "plaid_secret": "test-sec",
                    "plaid_env": "sandbox",
                    "access_tokens": {},
                }
            )
        )

        # Mock sandbox public_token/create
        sandbox_resp = MagicMock()
        sandbox_resp.json.return_value = {"public_token": "public-sandbox-auto"}
        sandbox_resp.raise_for_status = MagicMock()

        # Mock exchange
        exchange_resp = MagicMock()
        exchange_resp.json.return_value = {"access_token": "access-sandbox-final"}
        exchange_resp.raise_for_status = MagicMock()

        mock_post.side_effect = [sandbox_resp, exchange_resp]

        container = MagicMock()
        container.paths.plugin_dir = tmp_path

        args = MagicMock()
        args.sandbox = True
        args.institution_name = "First Platypus Bank"

        result = _cmd_plaid_auth(args, container)

        assert result == 0
        saved = json.loads(config_path.read_text())
        assert "First Platypus Bank" in saved["access_tokens"]
        assert saved["access_tokens"]["First Platypus Bank"] == "access-sandbox-final"

    def test_placeholder_credentials_rejected(self, tmp_path: Path) -> None:
        from plugins.plaid_connector.cli import _cmd_plaid_auth

        plugin_dir = tmp_path / "plaid_connector"
        plugin_dir.mkdir()
        config_path = plugin_dir / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "plaid_client_id": "your_key_here",
                    "plaid_secret": "your_key_here",
                    "plaid_env": "sandbox",
                    "access_tokens": {},
                }
            )
        )

        container = MagicMock()
        container.paths.plugin_dir = tmp_path

        args = MagicMock()
        args.sandbox = True

        result = _cmd_plaid_auth(args, container)

        assert result == 1

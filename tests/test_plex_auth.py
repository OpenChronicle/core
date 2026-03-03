"""Tests for Plex PIN-based authentication flow."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.plex_connector.plex_auth import PlexAuthFlow


class TestPlexAuthFlow:
    """Unit tests for PlexAuthFlow."""

    def setup_method(self) -> None:
        self.client_id = "test-client-id-1234"
        self.flow = PlexAuthFlow(self.client_id)

    @patch("plugins.plex_connector.plex_auth.httpx.post")
    def test_request_pin_parses_response(self, mock_post: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 12345, "code": "ABCD"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        pin_id, code = self.flow.request_pin()

        assert pin_id == 12345
        assert code == "ABCD"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["params"] == {"strong": "true"}
        headers = call_kwargs.kwargs["headers"]
        assert headers["X-Plex-Client-Identifier"] == self.client_id
        assert headers["X-Plex-Product"] == "OpenChronicle"

    def test_auth_url_builds_correct_url(self) -> None:
        url = self.flow.auth_url("ABCD")

        assert "https://app.plex.tv/auth" in url
        assert f"clientID={self.client_id}" in url
        assert "code=ABCD" in url
        assert "OpenChronicle" in url

    @patch("plugins.plex_connector.plex_auth.httpx.get")
    def test_check_pin_returns_token_when_claimed(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"authToken": "my-secret-token"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        token = self.flow.check_pin(12345, "ABCD")

        assert token == "my-secret-token"

    @patch("plugins.plex_connector.plex_auth.httpx.get")
    def test_check_pin_returns_none_when_pending(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"authToken": None}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        token = self.flow.check_pin(12345, "ABCD")

        assert token is None

    @patch("plugins.plex_connector.plex_auth.httpx.get")
    def test_check_pin_returns_none_for_empty_string(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"authToken": ""}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        token = self.flow.check_pin(12345, "ABCD")

        assert token is None

    @patch("plugins.plex_connector.plex_auth.time.sleep")
    @patch("plugins.plex_connector.plex_auth.httpx.get")
    def test_poll_for_token_succeeds_after_retries(self, mock_get: MagicMock, mock_sleep: MagicMock) -> None:
        pending_resp = MagicMock()
        pending_resp.json.return_value = {"authToken": None}
        pending_resp.raise_for_status = MagicMock()

        success_resp = MagicMock()
        success_resp.json.return_value = {"authToken": "final-token"}
        success_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [pending_resp, pending_resp, success_resp]

        token = self.flow.poll_for_token(12345, "ABCD", timeout=120, interval=0.01)

        assert token == "final-token"
        assert mock_get.call_count == 3

    @patch("plugins.plex_connector.plex_auth.time.monotonic")
    @patch("plugins.plex_connector.plex_auth.time.sleep")
    @patch("plugins.plex_connector.plex_auth.httpx.get")
    def test_poll_for_token_raises_timeout(
        self,
        mock_get: MagicMock,
        mock_sleep: MagicMock,
        mock_monotonic: MagicMock,
    ) -> None:
        pending_resp = MagicMock()
        pending_resp.json.return_value = {"authToken": None}
        pending_resp.raise_for_status = MagicMock()
        mock_get.return_value = pending_resp

        # First call sets deadline (0 + 5 = 5), second+ exceed it
        mock_monotonic.side_effect = [0.0, 1.0, 6.0]

        with pytest.raises(TimeoutError, match="timed out"):
            self.flow.poll_for_token(12345, "ABCD", timeout=5, interval=0.01)


class TestCmdPlexAuth:
    """Integration tests for _cmd_plex_auth (plugin CLI) with mocked dependencies."""

    @patch("plugins.plex_connector.cli.webbrowser")
    @patch("plugins.plex_connector.plex_auth.time.sleep")
    @patch("plugins.plex_connector.plex_auth.httpx.get")
    @patch("plugins.plex_connector.plex_auth.httpx.post")
    def test_end_to_end_auth_writes_token(
        self,
        mock_post: MagicMock,
        mock_get: MagicMock,
        mock_sleep: MagicMock,
        mock_webbrowser: MagicMock,
        tmp_path: Path,
    ) -> None:
        from plugins.plex_connector.cli import _cmd_plex_auth

        # Setup config
        plugin_dir = tmp_path / "plex_connector"
        plugin_dir.mkdir()
        config_path = plugin_dir / "config.json"
        config_path.write_text(json.dumps({"plex_url": "http://localhost:32400"}))

        # Mock PIN request
        pin_resp = MagicMock()
        pin_resp.json.return_value = {"id": 99, "code": "WXYZ"}
        pin_resp.raise_for_status = MagicMock()
        mock_post.return_value = pin_resp

        # Mock check_pin → token on first poll
        token_resp = MagicMock()
        token_resp.json.return_value = {"authToken": "real-plex-token-1234"}
        token_resp.raise_for_status = MagicMock()
        mock_get.return_value = token_resp

        # Mock container with paths
        container = MagicMock()
        container.paths.plugin_dir = tmp_path

        args = MagicMock()
        result = _cmd_plex_auth(args, container)

        assert result == 0
        mock_webbrowser.open.assert_called_once()

        saved = json.loads(config_path.read_text())
        assert saved["plex_token"] == "real-plex-token-1234"
        assert saved["client_id"]  # Should be a UUID

    @patch("plugins.plex_connector.cli.webbrowser")
    @patch("plugins.plex_connector.plex_auth.time.sleep")
    @patch("plugins.plex_connector.plex_auth.httpx.get")
    @patch("plugins.plex_connector.plex_auth.httpx.post")
    def test_reuses_existing_client_id(
        self,
        mock_post: MagicMock,
        mock_get: MagicMock,
        mock_sleep: MagicMock,
        mock_webbrowser: MagicMock,
        tmp_path: Path,
    ) -> None:
        from plugins.plex_connector.cli import _cmd_plex_auth

        existing_id = "my-existing-client-id"
        plugin_dir = tmp_path / "plex_connector"
        plugin_dir.mkdir()
        config_path = plugin_dir / "config.json"
        config_path.write_text(json.dumps({"client_id": existing_id}))

        pin_resp = MagicMock()
        pin_resp.json.return_value = {"id": 1, "code": "CODE"}
        pin_resp.raise_for_status = MagicMock()
        mock_post.return_value = pin_resp

        token_resp = MagicMock()
        token_resp.json.return_value = {"authToken": "tok"}
        token_resp.raise_for_status = MagicMock()
        mock_get.return_value = token_resp

        container = MagicMock()
        container.paths.plugin_dir = tmp_path

        args = MagicMock()
        _cmd_plex_auth(args, container)

        # Verify the POST used the existing client_id
        call_headers = mock_post.call_args.kwargs["headers"]
        assert call_headers["X-Plex-Client-Identifier"] == existing_id

        saved = json.loads(config_path.read_text())
        assert saved["client_id"] == existing_id

    @patch("plugins.plex_connector.cli.webbrowser")
    @patch("plugins.plex_connector.plex_auth.time.sleep")
    @patch("plugins.plex_connector.plex_auth.httpx.get")
    @patch("plugins.plex_connector.plex_auth.httpx.post")
    def test_client_id_auto_generated_and_persisted(
        self,
        mock_post: MagicMock,
        mock_get: MagicMock,
        mock_sleep: MagicMock,
        mock_webbrowser: MagicMock,
        tmp_path: Path,
    ) -> None:
        from plugins.plex_connector.cli import _cmd_plex_auth

        plugin_dir = tmp_path / "plex_connector"
        plugin_dir.mkdir()
        config_path = plugin_dir / "config.json"
        config_path.write_text(json.dumps({}))

        pin_resp = MagicMock()
        pin_resp.json.return_value = {"id": 1, "code": "X"}
        pin_resp.raise_for_status = MagicMock()
        mock_post.return_value = pin_resp

        token_resp = MagicMock()
        token_resp.json.return_value = {"authToken": "t"}
        token_resp.raise_for_status = MagicMock()
        mock_get.return_value = token_resp

        container = MagicMock()
        container.paths.plugin_dir = tmp_path

        args = MagicMock()
        _cmd_plex_auth(args, container)

        saved = json.loads(config_path.read_text())
        client_id = saved["client_id"]
        assert client_id  # Non-empty
        assert len(client_id) == 36  # UUID format: 8-4-4-4-12

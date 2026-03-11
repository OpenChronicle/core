"""Tests for the ``oc openwebui`` CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from openchronicle.core.domain.models.conversation import Conversation
from openchronicle.core.domain.models.project import Project
from openchronicle.interfaces.cli.commands.openwebui import (
    cmd_openwebui_list,
    cmd_openwebui_new,
    cmd_openwebui_url,
)


def _make_args(**kwargs: object) -> MagicMock:
    args = MagicMock()
    for k, v in kwargs.items():
        setattr(args, k, v)
    return args


def _make_container(project: Project | None = None) -> MagicMock:
    container = MagicMock()
    container.storage.get_project.return_value = project
    container.storage.list_conversations.return_value = []
    container.emit_event = MagicMock()
    return container


_TEST_PROJECT = Project(id="proj-1", name="Test Project")


class TestOpenwebuiNew:
    def test_creates_conversation_and_prints_url(self, capsys: object) -> None:
        container = _make_container(_TEST_PROJECT)
        args = _make_args(project_id="proj-1", title="My Session")

        with patch("openchronicle.interfaces.cli.commands.openwebui.HTTPConfig") as mock_cfg:
            mock_cfg.from_env.return_value = MagicMock(host="127.0.0.1", port=8000)
            result = cmd_openwebui_new(args, container)

        assert result == 0
        container.storage.add_conversation.assert_called_once()
        container.emit_event.assert_called_once()

    def test_missing_project_id_returns_error(self, capsys: object) -> None:
        container = _make_container()
        args = _make_args(project_id=None)

        with patch.dict("os.environ", {}, clear=False):
            result = cmd_openwebui_new(args, container)

        assert result == 1

    def test_invalid_project_returns_error(self) -> None:
        container = _make_container(project=None)
        args = _make_args(project_id="nonexistent")

        with patch("openchronicle.interfaces.cli.commands.openwebui.HTTPConfig") as mock_cfg:
            mock_cfg.from_env.return_value = MagicMock(host="127.0.0.1", port=8000)
            result = cmd_openwebui_new(args, container)

        assert result == 1


class TestOpenwebuiUrl:
    def test_prints_project_url(self, capsys: object) -> None:
        container = _make_container(_TEST_PROJECT)
        args = _make_args(project_id="proj-1")

        with patch("openchronicle.interfaces.cli.commands.openwebui.HTTPConfig") as mock_cfg:
            mock_cfg.from_env.return_value = MagicMock(host="127.0.0.1", port=8000)
            result = cmd_openwebui_url(args, container)

        assert result == 0

    def test_missing_project_id_returns_error(self) -> None:
        container = _make_container()
        args = _make_args(project_id=None)

        with patch.dict("os.environ", {}, clear=False):
            result = cmd_openwebui_url(args, container)

        assert result == 1


class TestOpenwebuiList:
    def test_lists_webui_conversations(self, capsys: object) -> None:
        container = _make_container(_TEST_PROJECT)
        convo = Conversation(id="c1", project_id="proj-1", title="Session 1", mode="webui")
        container.storage.list_conversations.return_value = [convo]
        args = _make_args(project_id="proj-1")

        result = cmd_openwebui_list(args, container)

        assert result == 0
        container.storage.list_conversations.assert_called_with(project_id="proj-1")

    def test_no_conversations_shows_help(self, capsys: object) -> None:
        container = _make_container(_TEST_PROJECT)
        container.storage.list_conversations.return_value = []
        args = _make_args(project_id="proj-1")

        result = cmd_openwebui_list(args, container)

        assert result == 0

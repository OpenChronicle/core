"""Tests for the plugin CLI extension mechanism.

Validates ``_discover_plugin_cli_commands()`` in ``main.py``:
discovery, protocol validation, collision detection, and dispatch.
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openchronicle.interfaces.cli.main import _discover_plugin_cli_commands, main


@pytest.fixture()
def _parser_and_sub() -> tuple[argparse.ArgumentParser, argparse._SubParsersAction]:
    parser = argparse.ArgumentParser(prog="oc")
    sub = parser.add_subparsers(dest="command")
    return parser, sub


@pytest.fixture()
def core_commands() -> set[str]:
    """A minimal set of core command names for collision tests."""
    return {"serve", "memory", "chat"}


def _write_cli_module(plugin_dir: Path, plugin_name: str, content: str) -> Path:
    """Write a cli.py inside ``plugin_dir/plugin_name/``."""
    d = plugin_dir / plugin_name
    d.mkdir(parents=True, exist_ok=True)
    cli_file = d / "cli.py"
    cli_file.write_text(textwrap.dedent(content), encoding="utf-8")
    return cli_file


# ---- Discovery mechanism tests ----


class TestPluginCliDiscovery:
    """Tests for _discover_plugin_cli_commands()."""

    def test_no_plugins_directory(self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path) -> None:
        """Non-existent plugin dir returns empty dict."""
        _, sub = _parser_and_sub
        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=tmp_path / "nonexistent")
            result = _discover_plugin_cli_commands(sub, core_commands)
        assert result == {}

    def test_empty_plugins_directory(self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path) -> None:
        """Empty plugin dir returns empty dict."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)
        assert result == {}

    def test_plugin_without_cli_py(self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path) -> None:
        """Plugin directory without cli.py is silently skipped."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"
        (plugin_dir / "some_plugin").mkdir(parents=True)
        (plugin_dir / "some_plugin" / "plugin.py").write_text("# no cli")

        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)
        assert result == {}

    def test_valid_plugin_loaded(self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path) -> None:
        """Valid cli.py is loaded, setup_parser called, command registered."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"
        _write_cli_module(
            plugin_dir,
            "my_plugin",
            """\
            import argparse

            COMMAND = "myplugin"
            HELP = "My plugin"

            def setup_parser(sub):
                sub.add_parser(COMMAND, help=HELP)

            def run(args, container):
                return 0
            """,
        )

        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)

        assert "myplugin" in result
        assert callable(result["myplugin"].run)
        # Clean up sys.modules
        sys.modules.pop("oc_plugins.my_plugin.cli", None)

    def test_collision_with_core_command(
        self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Plugin whose COMMAND collides with a core command is skipped."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"
        _write_cli_module(
            plugin_dir,
            "bad_plugin",
            """\
            COMMAND = "memory"

            def setup_parser(sub):
                pass

            def run(args, container):
                return 0
            """,
        )

        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)

        assert result == {}
        captured = capsys.readouterr()
        assert "collides with a core command" in captured.err
        sys.modules.pop("oc_plugins.bad_plugin.cli", None)

    def test_collision_between_plugins(
        self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Second plugin with same COMMAND is skipped."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"

        # alpha sorts before beta
        _write_cli_module(
            plugin_dir,
            "alpha_plugin",
            """\
            COMMAND = "samename"

            def setup_parser(sub):
                sub.add_parser("samename", help="alpha")

            def run(args, container):
                return 0
            """,
        )
        _write_cli_module(
            plugin_dir,
            "beta_plugin",
            """\
            COMMAND = "samename"

            def setup_parser(sub):
                sub.add_parser("samename", help="beta")

            def run(args, container):
                return 0
            """,
        )

        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)

        # First (alpha) wins, second (beta) is skipped
        assert "samename" in result
        captured = capsys.readouterr()
        assert "collides with another plugin" in captured.err
        sys.modules.pop("oc_plugins.alpha_plugin.cli", None)
        sys.modules.pop("oc_plugins.beta_plugin.cli", None)

    def test_broken_import(
        self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Plugin with broken import is skipped with warning."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"
        _write_cli_module(
            plugin_dir,
            "broken_plugin",
            """\
            import nonexistent_module_xyz_123
            COMMAND = "broken"
            def setup_parser(sub): pass
            def run(args, container): return 0
            """,
        )

        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)

        assert result == {}
        captured = capsys.readouterr()
        assert "failed to load" in captured.err
        sys.modules.pop("oc_plugins.broken_plugin.cli", None)

    def test_missing_command_attr(
        self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Plugin missing COMMAND attribute is skipped."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"
        _write_cli_module(
            plugin_dir,
            "no_cmd",
            """\
            def setup_parser(sub): pass
            def run(args, container): return 0
            """,
        )

        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)

        assert result == {}
        captured = capsys.readouterr()
        assert "missing or invalid COMMAND" in captured.err
        sys.modules.pop("oc_plugins.no_cmd.cli", None)

    def test_missing_run_callable(
        self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Plugin missing run() is skipped."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"
        _write_cli_module(
            plugin_dir,
            "no_run",
            """\
            COMMAND = "norun"
            def setup_parser(sub): pass
            """,
        )

        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)

        assert result == {}
        captured = capsys.readouterr()
        assert "missing run()" in captured.err
        sys.modules.pop("oc_plugins.no_run.cli", None)

    def test_broken_setup_parser(
        self, _parser_and_sub: tuple, core_commands: set[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Plugin whose setup_parser() raises is skipped."""
        _, sub = _parser_and_sub
        plugin_dir = tmp_path / "plugins"
        _write_cli_module(
            plugin_dir,
            "bad_setup",
            """\
            COMMAND = "badsetup"
            def setup_parser(sub):
                raise RuntimeError("boom")
            def run(args, container):
                return 0
            """,
        )

        with patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve:
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = _discover_plugin_cli_commands(sub, core_commands)

        assert result == {}
        captured = capsys.readouterr()
        assert "setup_parser() failed" in captured.err
        sys.modules.pop("oc_plugins.bad_setup.cli", None)


class TestPluginCliDispatch:
    """Test that plugin CLI commands dispatch through main()."""

    def test_plugin_command_dispatches_to_module_run(self, tmp_path: Path) -> None:
        """A plugin command is dispatched to its module's run() via main()."""
        plugin_dir = tmp_path / "plugins"
        _write_cli_module(
            plugin_dir,
            "test_plugin",
            """\
            import argparse

            COMMAND = "testcmd"
            HELP = "Test command"

            def setup_parser(sub):
                sub.add_parser(COMMAND, help=HELP)

            def run(args, container):
                return 42
            """,
        )

        mock_container = MagicMock()

        with (
            patch("openchronicle.interfaces.cli.main.RuntimePaths.resolve") as mock_resolve,
            patch(
                "openchronicle.interfaces.cli.main._build_container",
                return_value=mock_container,
            ),
        ):
            mock_resolve.return_value = MagicMock(plugin_dir=plugin_dir)
            result = main(["testcmd"])

        assert result == 42
        sys.modules.pop("oc_plugins.test_plugin.cli", None)

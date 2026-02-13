"""Tests for the oc provider CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from openchronicle.interfaces.cli.main import main


@pytest.fixture()
def config_dir(tmp_path: Path) -> str:
    return str(tmp_path / "config")


class TestProviderList:
    def test_list_output_contains_all_providers(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["provider", "list"])
        out = capsys.readouterr().out
        assert "openai" in out
        assert "anthropic" in out
        assert "gemini" in out
        assert "groq" in out
        assert "ollama" in out
        assert "xai" in out

    def test_list_shows_models(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["provider", "list"])
        out = capsys.readouterr().out
        assert "gpt-4o-mini" in out
        assert "grok-3" in out


class TestProviderSetupNonInteractive:
    def test_setup_creates_files(self, config_dir: str, capsys: pytest.CaptureFixture[str]) -> None:
        ret = main(["provider", "setup", "--provider", "openai", "--config-dir", config_dir])
        assert ret == 0
        models_dir = Path(config_dir) / "models"
        files = list(models_dir.glob("*.json"))
        assert len(files) == 3

    def test_setup_with_model_filter(self, config_dir: str) -> None:
        ret = main(["provider", "setup", "--provider", "openai", "--models", "gpt-4o-mini", "--config-dir", config_dir])
        assert ret == 0
        models_dir = Path(config_dir) / "models"
        files = list(models_dir.glob("*.json"))
        assert len(files) == 1

    def test_setup_unknown_provider(self, config_dir: str, capsys: pytest.CaptureFixture[str]) -> None:
        ret = main(["provider", "setup", "--provider", "nonexistent", "--config-dir", config_dir])
        assert ret == 1
        out = capsys.readouterr().out
        assert "Unknown provider" in out


class TestProviderCustom:
    def test_custom_creates_file(self, config_dir: str) -> None:
        ret = main(
            [
                "provider",
                "custom",
                "--provider",
                "myapi",
                "--model",
                "my-model",
                "--endpoint",
                "https://example.com/v1/chat",
                "--config-dir",
                config_dir,
            ]
        )
        assert ret == 0
        models_dir = Path(config_dir) / "models"
        files = list(models_dir.glob("*.json"))
        assert len(files) == 1


class TestProviderSetupInteractive:
    def test_interactive_provider_selection(self, config_dir: str, capsys: pytest.CaptureFixture[str]) -> None:
        # Select provider 1 (openai), press Enter for key (use env var), Enter for all models
        inputs = iter(["1", "", ""])
        with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value=""):
            ret = main(["provider", "setup", "--config-dir", config_dir])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Created" in out

    def test_interactive_with_key(self, config_dir: str) -> None:
        # Select provider 1 (openai), enter a key, Enter for all models
        inputs = iter(["1", ""])
        with patch("builtins.input", side_effect=inputs), patch("getpass.getpass", return_value="test-key-123"):
            ret = main(["provider", "setup", "--config-dir", config_dir])
        assert ret == 0


class TestProviderNoSubcommand:
    def test_no_subcommand_prints_usage(self, capsys: pytest.CaptureFixture[str]) -> None:
        ret = main(["provider"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Usage" in out or "list" in out

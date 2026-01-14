"""Tests for enhanced diagnose output with model config discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from openchronicle.core.application.use_cases.diagnose_runtime import execute


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a config directory structure for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    models_dir = config_dir / "models"
    models_dir.mkdir(parents=True)
    return config_dir


def test_diagnose_reports_models_dir_when_exists(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose reports models directory path and existence."""
    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    assert report.models_dir == str(temp_config_dir / "models")
    assert report.models_dir_exists is True


def test_diagnose_reports_models_dir_missing(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose reports when models directory doesn't exist."""
    config_dir_no_models = temp_config_dir.parent / "nonexistent"
    monkeypatch.setenv("OC_CONFIG_DIR", str(config_dir_no_models))

    report = execute()

    assert report.models_dir_exists is False
    assert report.model_config_files_count == 0
    assert report.model_config_provider_summary == {}


def test_diagnose_discovers_valid_model_configs(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose discovers and counts model config files."""
    models_dir = temp_config_dir / "models"

    # Create test configs
    openai_config = {
        "provider": "openai",
        "model": "gpt-4o",
        "enabled": True,
        "display_name": "OpenAI GPT-4o",
        "api_config": {
            "auth_header": "Authorization",
            "auth_format": "Bearer {api_key}",
        },
    }

    anthropic_config = {
        "provider": "anthropic",
        "model": "claude-3-sonnet",
        "enabled": True,
        "display_name": "Anthropic Claude 3 Sonnet",
        "api_config": {
            "auth_header": "x-api-key",
            "auth_format": "{api_key}",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    }

    (models_dir / "openai_gpt4o.json").write_text(json.dumps(openai_config))
    (models_dir / "anthropic_claude.json").write_text(json.dumps(anthropic_config))

    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    assert report.model_config_files_count == 2
    assert "openai" in report.model_config_provider_summary
    assert "anthropic" in report.model_config_provider_summary


def test_diagnose_counts_enabled_disabled_configs(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose reports enabled/disabled count per provider."""
    models_dir = temp_config_dir / "models"

    # Create enabled OpenAI config
    enabled_config = {
        "provider": "openai",
        "model": "gpt-4o",
        "enabled": True,
        "api_config": {"auth_format": "Bearer {api_key}"},
    }

    # Create disabled OpenAI config
    disabled_config = {
        "provider": "openai",
        "model": "gpt-4-turbo",
        "enabled": False,
        "api_config": {"auth_format": "Bearer {api_key}"},
    }

    (models_dir / "openai_enabled.json").write_text(json.dumps(enabled_config))
    (models_dir / "openai_disabled.json").write_text(json.dumps(disabled_config))

    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    assert report.model_config_files_count == 2
    openai_summary = report.model_config_provider_summary.get("openai", {})
    assert openai_summary.get("enabled_count") == 1
    assert openai_summary.get("disabled_count") == 1


def test_diagnose_detects_api_key_requirements(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose reports how many configs require API keys."""
    models_dir = temp_config_dir / "models"

    # Config with auth_format (requires key)
    with_key_req = {
        "provider": "openai",
        "model": "gpt-4o",
        "enabled": True,
        "api_config": {
            "auth_format": "Bearer {api_key}",
        },
    }

    # Config without auth (no key required)
    no_key_req = {"provider": "ollama", "model": "llama2", "enabled": True, "api_config": {}}

    (models_dir / "openai.json").write_text(json.dumps(with_key_req))
    (models_dir / "ollama.json").write_text(json.dumps(no_key_req))

    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    openai_summary = report.model_config_provider_summary.get("openai", {})
    ollama_summary = report.model_config_provider_summary.get("ollama", {})

    assert openai_summary.get("requires_api_key_count") == 1
    assert ollama_summary.get("requires_api_key_count") == 0


def test_diagnose_detects_api_key_set_status(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose reports API key presence without exposing values."""
    models_dir = temp_config_dir / "models"

    # Config with inline API key
    with_inline_key = {
        "provider": "openai",
        "model": "gpt-4o-inline",
        "enabled": True,
        "api_config": {
            "auth_format": "Bearer {api_key}",
            "api_key": "sk-test-key-inline",  # Inline key (for testing)
        },
    }

    # Config with env var that exists
    with_env_key = {
        "provider": "openai",
        "model": "gpt-4o-env",
        "enabled": True,
        "api_config": {"auth_format": "Bearer {api_key}", "api_key_env": "MY_CUSTOM_KEY_VAR"},
    }

    # Config with missing key
    without_key = {
        "provider": "openai",
        "model": "gpt-4o-missing",
        "enabled": True,
        "api_config": {"auth_format": "Bearer {api_key}", "api_key_env": "MISSING_KEY_VAR"},
    }

    (models_dir / "openai_inline.json").write_text(json.dumps(with_inline_key))
    (models_dir / "openai_env.json").write_text(json.dumps(with_env_key))
    (models_dir / "openai_missing.json").write_text(json.dumps(without_key))

    # Set the custom env var
    monkeypatch.setenv("MY_CUSTOM_KEY_VAR", "test-value")
    monkeypatch.delenv("MISSING_KEY_VAR", raising=False)
    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    openai_summary = report.model_config_provider_summary.get("openai", {})
    assert openai_summary.get("requires_api_key_count") == 3
    assert openai_summary.get("api_key_set_count") == 2  # inline + env
    assert openai_summary.get("api_key_missing_count") == 1


def test_diagnose_reports_standard_env_mapping(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose uses standard API key env var names (OPENAI_API_KEY, etc.)."""
    models_dir = temp_config_dir / "models"

    # Config without custom api_key_env (should use standard)
    config = {
        "provider": "openai",
        "model": "gpt-4o",
        "enabled": True,
        "api_config": {"auth_format": "Bearer {api_key}"},
    }

    (models_dir / "openai.json").write_text(json.dumps(config))

    # Set standard env var
    monkeypatch.setenv("OPENAI_API_KEY", "sk-standard-key")
    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    openai_summary = report.model_config_provider_summary.get("openai", {})
    assert openai_summary.get("api_key_set_count") == 1


def test_diagnose_handles_malformed_json(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose reports malformed JSON files without crashing."""
    models_dir = temp_config_dir / "models"

    # Valid config
    valid = {"provider": "openai", "model": "gpt-4o", "enabled": True, "api_config": {}}
    (models_dir / "valid.json").write_text(json.dumps(valid))

    # Invalid JSON
    (models_dir / "broken.json").write_text("{ invalid json }")

    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    # Should report 1 valid file
    assert report.model_config_files_count == 1

    # Should report error for broken file
    assert "broken.json" in report.model_config_load_errors
    assert "Invalid JSON" in report.model_config_load_errors["broken.json"]

    # Should still have openai provider from valid config
    assert "openai" in report.model_config_provider_summary


def test_diagnose_handles_missing_provider_field(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose reports configs with missing required fields."""
    models_dir = temp_config_dir / "models"

    # Missing provider field
    missing_provider = {"model": "gpt-4o", "enabled": True, "api_config": {}}

    # Missing model field
    missing_model = {"provider": "openai", "enabled": True, "api_config": {}}

    (models_dir / "missing_provider.json").write_text(json.dumps(missing_provider))
    (models_dir / "missing_model.json").write_text(json.dumps(missing_model))

    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    # Files should be counted but errors logged
    assert report.model_config_files_count == 2
    assert "missing_provider.json" in report.model_config_load_errors
    assert "missing_model.json" in report.model_config_load_errors


def test_diagnose_deterministic_ordering(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose results are deterministically ordered for consistent output."""
    models_dir = temp_config_dir / "models"

    # Create configs in reverse alphabetical order
    for name in ["z_config", "m_config", "a_config"]:
        config = {"provider": "openai", "model": f"model-{name}", "enabled": True, "api_config": {}}
        (models_dir / f"{name}.json").write_text(json.dumps(config))

    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    report = execute()

    # Should have all 3 configs
    assert report.model_config_files_count == 3

    # Provider summary should exist
    assert "openai" in report.model_config_provider_summary

    # No errors (no JSON parse errors)
    assert len(report.model_config_load_errors) == 0


def test_diagnose_multiple_providers(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose correctly aggregates multiple providers."""
    models_dir = temp_config_dir / "models"

    providers_config = {
        "openai": {
            "provider": "openai",
            "model": "gpt-4o",
            "enabled": True,
            "api_config": {"auth_format": "Bearer {api_key}"},
        },
        "anthropic": {
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "enabled": True,
            "api_config": {"auth_format": "{api_key}"},
        },
        "ollama": {"provider": "ollama", "model": "llama2", "enabled": True, "api_config": {}},
        "groq": {
            "provider": "groq",
            "model": "mixtral-8x7b",
            "enabled": False,
            "api_config": {"auth_format": "Bearer {api_key}"},
        },
    }

    for name, config in providers_config.items():
        (models_dir / f"{name}.json").write_text(json.dumps(config))

    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    assert report.model_config_files_count == 4
    assert len(report.model_config_provider_summary) == 4

    # Verify each provider summary has expected structure
    for provider in ["openai", "anthropic", "ollama", "groq"]:
        summary = report.model_config_provider_summary.get(provider, {})
        assert "enabled_count" in summary
        assert "disabled_count" in summary
        assert "requires_api_key_count" in summary
        assert "api_key_set_count" in summary
        assert "api_key_missing_count" in summary


def test_diagnose_no_secret_leakage_in_errors(temp_config_dir: Path, monkeypatch: Any) -> None:
    """Diagnose never includes secret values in error messages."""
    models_dir = temp_config_dir / "models"

    # Create a config with inline secret
    secret_config = {
        "provider": "openai",
        "model": "gpt-4o",
        "enabled": True,
        "api_config": {"api_key": "sk-super-secret-key-12345", "auth_format": "Bearer {api_key}"},
    }

    (models_dir / "secret.json").write_text(json.dumps(secret_config))

    monkeypatch.setenv("OC_CONFIG_DIR", str(temp_config_dir))

    report = execute()

    # Convert entire report to string and check for secret
    report_str = str(report)
    assert "sk-super-secret-key-12345" not in report_str

    # Check error messages
    error_str = str(report.model_config_load_errors)
    assert "sk-super-secret-key-12345" not in error_str

    # Check provider summary (should have counts, not keys)
    summary_str = str(report.model_config_provider_summary)
    assert "sk-super-secret-key-12345" not in summary_str

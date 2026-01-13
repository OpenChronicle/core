"""Tests for model configuration loading and secret resolution."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from openchronicle.core.application.config.model_config import ConfigError, ModelConfigLoader, ResolvedModelConfig


def test_resolved_model_config_repr_hides_secrets() -> None:
    """Verify that repr() does not expose secret values."""
    config = ResolvedModelConfig(
        provider="openai",
        model="gpt-4o",
        api_key="sk-secret-key-12345",
        auth_token="secret-token",
    )

    repr_str = repr(config)

    # Verify secrets are not in repr
    assert "sk-secret-key-12345" not in repr_str
    assert "secret-token" not in repr_str

    # Verify safe markers are present
    assert "<set>" in repr_str
    assert "api_key=<set>" in repr_str
    assert "auth_token=<set>" in repr_str


def test_load_model_config_openai() -> None:
    """Test loading OpenAI model config with api_key_file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        secrets_dir = config_dir / "secrets"

        models_dir.mkdir(parents=True)
        secrets_dir.mkdir(parents=True)

        # Create API key file
        (secrets_dir / "openai_api_key").write_text("sk-test-key-12345\n")

        # Create model config
        model_config = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key_file": "secrets/openai_api_key",
        }
        (models_dir / "openai_gpt4o_mini.json").write_text(json.dumps(model_config))

        loader = ModelConfigLoader(str(config_dir))
        resolved = loader.load_model_config("openai_gpt4o_mini")

        assert resolved.provider == "openai"
        assert resolved.model == "gpt-4o-mini"
        assert resolved.api_key == "sk-test-key-12345"


def test_env_var_override_file() -> None:
    """Test that env vars override file values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        secrets_dir = config_dir / "secrets"

        models_dir.mkdir(parents=True)
        secrets_dir.mkdir(parents=True)

        # Create API key file with one value
        (secrets_dir / "openai_api_key").write_text("sk-file-key\n")

        # Create model config
        model_config = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_file": "secrets/openai_api_key",
        }
        (models_dir / "test_model.json").write_text(json.dumps(model_config))

        loader = ModelConfigLoader(str(config_dir))

        # Without env var, should use file
        resolved = loader.load_model_config("test_model")
        assert resolved.api_key == "sk-file-key"

        # With env var, should override
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"}):
            resolved = loader.load_model_config("test_model")
            assert resolved.api_key == "sk-env-key"


def test_missing_required_model_raises() -> None:
    """Test that missing required fields raise ConfigError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        models_dir.mkdir(parents=True)

        # Missing 'provider' field
        model_config = {"model": "test"}
        (models_dir / "bad_model.json").write_text(json.dumps(model_config))

        loader = ModelConfigLoader(str(config_dir))

        with pytest.raises(ConfigError, match="'provider' is required"):
            loader.load_model_config("bad_model")


def test_missing_model_file_raises() -> None:
    """Test that missing model file raises ConfigError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = ModelConfigLoader(tmpdir)

        with pytest.raises(ConfigError, match="Model config not found"):
            loader.load_model_config("nonexistent_model")


def test_missing_secret_file_raises() -> None:
    """Test that missing secret file raises ConfigError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        models_dir.mkdir(parents=True)

        # Config references missing secret file
        model_config = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_file": "secrets/missing_api_key",
        }
        (models_dir / "test_model.json").write_text(json.dumps(model_config))

        loader = ModelConfigLoader(str(config_dir))

        with pytest.raises(ConfigError, match="Failed to read secret file"):
            loader.load_model_config("test_model")


def test_ollama_base_url_env() -> None:
    """Test that base_url_env field is handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        models_dir.mkdir(parents=True)

        # Ollama config with base_url_env field
        model_config = {
            "provider": "ollama",
            "model": "mistral:7b",
            "base_url_env": "OLLAMA_HOST",
            "api_config": {"default_base_url": "http://localhost:11434"},
        }
        (models_dir / "ollama_model.json").write_text(json.dumps(model_config))

        loader = ModelConfigLoader(str(config_dir))

        # Without env var, use default
        resolved = loader.load_model_config("ollama_model")
        assert resolved.base_url == "http://localhost:11434"

        # With env var, use that
        with mock.patch.dict(os.environ, {"OLLAMA_HOST": "http://custom-ollama:11434"}):
            resolved = loader.load_model_config("ollama_model")
            assert resolved.base_url == "http://custom-ollama:11434"


def test_secret_not_in_error_messages() -> None:
    """Verify that secret values never appear in error messages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        secrets_dir = config_dir / "secrets"

        models_dir.mkdir(parents=True)
        secrets_dir.mkdir(parents=True)

        # Config with missing secret file
        model_config = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_file": "secrets/fake_key_value_12345",
        }
        (models_dir / "test_model.json").write_text(json.dumps(model_config))

        loader = ModelConfigLoader(str(config_dir))

        try:
            loader.load_model_config("test_model")
            pytest.fail("Should have raised ConfigError")
        except ConfigError as e:
            error_msg = str(e)
            # File path may be in error, but the actual secret shouldn't be
            assert "fake_key_value_12345" not in error_msg


def test_strip_whitespace_from_secrets() -> None:
    """Test that leading/trailing whitespace is stripped from secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        secrets_dir = config_dir / "secrets"

        models_dir.mkdir(parents=True)
        secrets_dir.mkdir(parents=True)

        # Create API key file with whitespace
        (secrets_dir / "openai_api_key").write_text("  sk-test-key-with-spaces  \n\n")

        # Create model config
        model_config = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_file": "secrets/openai_api_key",
        }
        (models_dir / "test_model.json").write_text(json.dumps(model_config))

        loader = ModelConfigLoader(str(config_dir))
        resolved = loader.load_model_config("test_model")

        assert resolved.api_key == "sk-test-key-with-spaces"


def test_malformed_json_raises() -> None:
    """Test that malformed JSON raises ConfigError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        models_dir.mkdir(parents=True)

        # Write invalid JSON
        (models_dir / "bad_json.json").write_text("{invalid json")

        loader = ModelConfigLoader(str(config_dir))

        with pytest.raises(ConfigError, match="Failed to load model config"):
            loader.load_model_config("bad_json")


def test_v1_style_model_extraction() -> None:
    """Test loading v1-style configs with api_config.model."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        models_dir = config_dir / "models"
        models_dir.mkdir(parents=True)

        # V1-style config with model in api_config
        model_config = {
            "provider": "openai",
            "api_config": {
                "model": "gpt-4o-turbo",
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "default_base_url": "https://api.openai.com/v1",
            },
        }
        (models_dir / "v1_style.json").write_text(json.dumps(model_config))

        loader = ModelConfigLoader(str(config_dir))
        resolved = loader.load_model_config("v1_style")

        assert resolved.provider == "openai"
        assert resolved.model == "gpt-4o-turbo"
        assert resolved.endpoint == "https://api.openai.com/v1/chat/completions"

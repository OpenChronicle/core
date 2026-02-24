"""Tests for v1-style model configuration loading."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from openchronicle.core.application.config.model_config import (
    ConfigError,
    ModelConfigEntry,
    ModelConfigLoader,
    ResolvedModelConfig,
    sort_model_configs,
)


def _write_config(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_configs_discovered_deterministically() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(models_dir / "z_model.json", {"provider": "openai", "model": "z", "api_config": {"api_key": "k"}})
        _write_config(models_dir / "a_model.json", {"provider": "openai", "model": "a", "api_config": {"api_key": "k"}})

        loader = ModelConfigLoader(tmpdir)
        filenames = [cfg.filename for cfg in loader.list_all()]

        assert filenames == ["a_model.json", "z_model.json"]


def test_enabled_false_is_excluded() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "enabled.json", {"provider": "openai", "model": "ok", "api_config": {"api_key": "k"}}
        )
        _write_config(
            models_dir / "disabled.json",
            {"provider": "openai", "model": "skip", "enabled": False, "api_config": {"api_key": "k"}},
        )

        loader = ModelConfigLoader(tmpdir)
        enabled_models = {cfg.model for cfg in loader.list_enabled()}

        assert enabled_models == {"ok"}
        with pytest.raises(ConfigError, match="not found or disabled"):
            loader.resolve("openai", "skip")


def test_inline_api_key_wins_over_env_actual() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {
                "provider": "openai",
                "model": "gpt",
                "api_config": {"api_key": "inline-key", "api_key_env": "OPENAI_API_KEY"},
            },
        )

        loader = ModelConfigLoader(tmpdir)
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=True):
            resolved = loader.resolve("openai", "gpt")
            assert resolved.api_key == "inline-key"


def test_env_used_when_inline_absent() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {
                "provider": "openai",
                "model": "gpt",
                "api_config": {
                    "api_key_env": "CUSTOM_KEY",
                    "auth_format": "Bearer {api_key}",
                    "auth_header": "Authorization",
                },
            },
        )

        loader = ModelConfigLoader(tmpdir)
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigError):
                loader.resolve("openai", "gpt")

        with mock.patch.dict(os.environ, {"CUSTOM_KEY": "from-env"}, clear=True):
            resolved = loader.resolve("openai", "gpt")
            assert resolved.api_key == "from-env"


def test_missing_api_key_errors_on_use() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {
                "provider": "openai",
                "model": "gpt",
                "api_config": {"auth_format": "Bearer {api_key}", "auth_header": "Authorization"},
            },
        )

        loader = ModelConfigLoader(tmpdir)
        # Loading does not raise
        assert loader.list_all()

        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigError, match="API key not configured"):
                loader.resolve("openai", "gpt")


def test_allows_no_api_key_when_not_required() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {
                "provider": "ollama",
                "model": "mixtral",
                "api_config": {},
            },
        )

        loader = ModelConfigLoader(tmpdir)
        resolved = loader.resolve("ollama", "mixtral")
        assert resolved.api_key is None


def test_repr_masks_api_key() -> None:
    cfg = ResolvedModelConfig(provider="p", model="m", api_key="secret", endpoint="e")
    text = repr(cfg)
    assert "secret" not in text
    assert "<set>" in text


def test_sort_helper_orders_deterministically() -> None:
    items = [
        ModelConfigEntry(provider="b", model="z", enabled=True, filename="z.json", display_name=None, api_config={}),
        ModelConfigEntry(provider="a", model="a", enabled=True, filename="a.json", display_name=None, api_config={}),
    ]
    sorted_items = sort_model_configs(items)
    assert [i.filename for i in sorted_items] == ["a.json", "z.json"]


# ---- Capability parsing ----


def test_capabilities_parsed_from_config_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {
                "provider": "openai",
                "model": "gpt-4o",
                "capabilities": {"text_generation": True, "vision": True, "function_calling": True},
                "api_config": {},
            },
        )

        loader = ModelConfigLoader(tmpdir)
        cfg = loader.list_all()[0]
        assert cfg.capabilities == {"text_generation": True, "vision": True, "function_calling": True}


def test_missing_capabilities_defaults_to_empty_dict() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {"provider": "openai", "model": "gpt", "api_config": {}},
        )

        loader = ModelConfigLoader(tmpdir)
        cfg = loader.list_all()[0]
        assert cfg.capabilities == {}


def test_invalid_capabilities_type_treated_as_empty() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {"provider": "openai", "model": "gpt", "capabilities": "not-a-dict", "api_config": {}},
        )

        loader = ModelConfigLoader(tmpdir)
        cfg = loader.list_all()[0]
        assert cfg.capabilities == {}


def test_get_capabilities_returns_correct_dict() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {
                "provider": "openai",
                "model": "gpt-4o",
                "capabilities": {"vision": True, "streaming": True},
                "api_config": {},
            },
        )

        loader = ModelConfigLoader(tmpdir)
        caps = loader.get_capabilities("openai", "gpt-4o")
        assert caps == {"vision": True, "streaming": True}


def test_get_capabilities_unknown_model_returns_empty() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        _write_config(
            models_dir / "model.json",
            {"provider": "openai", "model": "gpt", "api_config": {}},
        )

        loader = ModelConfigLoader(tmpdir)
        caps = loader.get_capabilities("nonexistent", "model")
        assert caps == {}

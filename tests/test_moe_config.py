"""Tests for MoE configuration loading."""

from __future__ import annotations

import os
from unittest.mock import patch

from openchronicle.core.application.config.settings import MoESettings, load_moe_settings


class TestMoEDefaults:
    def test_defaults(self) -> None:
        settings = MoESettings()
        assert settings.enabled is False
        assert settings.min_experts == 2
        assert settings.temperature is None


class TestMoEFromFileConfig:
    def test_from_file_config(self) -> None:
        settings = load_moe_settings(
            {
                "enabled": True,
                "min_experts": 3,
                "temperature": 0.7,
            }
        )
        assert settings.enabled is True
        assert settings.min_experts == 3
        assert settings.temperature == 0.7

    def test_partial_file_config(self) -> None:
        settings = load_moe_settings({"enabled": True})
        assert settings.enabled is True
        assert settings.min_experts == 2  # default
        assert settings.temperature is None  # default


class TestMoEEnvOverrides:
    def test_env_overrides_file_config(self) -> None:
        env = {
            "OC_MOE_ENABLED": "true",
            "OC_MOE_MIN_EXPERTS": "4",
            "OC_MOE_TEMPERATURE": "0.5",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = load_moe_settings({"enabled": False, "min_experts": 2})
        assert settings.enabled is True
        assert settings.min_experts == 4
        assert settings.temperature == 0.5

    def test_env_disabled(self) -> None:
        env = {"OC_MOE_ENABLED": "false"}
        with patch.dict(os.environ, env, clear=False):
            settings = load_moe_settings({"enabled": True})
        assert settings.enabled is False


class TestMoEEmptyConfig:
    def test_empty_dict(self) -> None:
        settings = load_moe_settings({})
        assert settings is not None
        assert settings.enabled is False

    def test_none(self) -> None:
        settings = load_moe_settings(None)
        assert settings is not None
        assert settings.enabled is False

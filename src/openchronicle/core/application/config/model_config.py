"""Model configuration loading with sensitive value resolution."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Configuration error with secret-safe messaging."""


@dataclass
class ResolvedModelConfig:
    """Model config with sensitive values resolved from files/env."""

    provider: str
    model: str
    endpoint: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    auth_token: str | None = None
    extra_config: dict[str, Any] | None = None

    def __repr__(self) -> str:
        """Secret-safe representation (no sensitive values printed)."""
        return (
            f"ResolvedModelConfig(provider={self.provider!r}, model={self.model!r}, "
            f"endpoint={self.endpoint!r}, base_url={self.base_url!r}, "
            f"api_key={'<set>' if self.api_key else 'None'}, "
            f"auth_token={'<set>' if self.auth_token else 'None'})"
        )


class ModelConfigLoader:
    """Load and resolve model configurations from JSON files with secret support."""

    def __init__(self, config_dir: str) -> None:
        """
        Initialize loader with config directory.

        Args:
            config_dir: Base configuration directory path
        """
        self.config_dir = Path(config_dir)
        self.models_dir = self.config_dir / "models"

    def load_model_config(self, model_name: str) -> ResolvedModelConfig:
        """
        Load and resolve a model configuration by name.

        Looks for <OC_CONFIG_DIR>/models/<model_name>.json

        Args:
            model_name: Model name (without .json extension)

        Returns:
            ResolvedModelConfig with all sensitive values resolved

        Raises:
            ConfigError: If file not found or required values missing
        """
        config_file = self.models_dir / f"{model_name}.json"

        if not config_file.exists():
            raise ConfigError(f"Model config not found: {config_file}")

        try:
            with open(config_file) as f:
                raw_config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise ConfigError(f"Failed to load model config {model_name}: {e}") from e

        return self._resolve_config(raw_config, model_name)

    def _resolve_config(self, raw_config: dict[str, Any], model_name: str) -> ResolvedModelConfig:
        """
        Resolve all sensitive values in a loaded config.

        Args:
            raw_config: Raw loaded JSON config
            model_name: Model name (for error messages)

        Returns:
            ResolvedModelConfig

        Raises:
            ConfigError: If required sensitive values cannot be resolved
        """
        provider = raw_config.get("provider")
        if not provider:
            raise ConfigError(f"Model config {model_name}: 'provider' is required")

        # For v1-style configs, extract from api_config.model if present
        model = raw_config.get("model")
        if not model:
            api_config = raw_config.get("api_config", {})
            model = api_config.get("model")
        if not model:
            raise ConfigError(f"Model config {model_name}: 'model' is required")

        # Resolve sensitive values
        api_key = self._resolve_sensitive_value(raw_config, "api_key")
        auth_token = self._resolve_sensitive_value(raw_config, "auth_token")

        # Handle base_url with env var override support
        base_url = None
        if "base_url_env" in raw_config:
            # Check env var specified in config
            env_var = raw_config["base_url_env"]
            base_url = os.getenv(env_var)
        if not base_url:
            # Fall back to explicit base_url or api_config.default_base_url
            base_url = raw_config.get("base_url") or (
                raw_config.get("api_config", {}).get("default_base_url") if raw_config.get("api_config") else None
            )

        endpoint = raw_config.get("endpoint") or (
            raw_config.get("api_config", {}).get("endpoint") if raw_config.get("api_config") else None
        )

        return ResolvedModelConfig(
            provider=provider,
            model=model,
            endpoint=endpoint,
            base_url=base_url,
            api_key=api_key,
            auth_token=auth_token,
            extra_config={
                k: v
                for k, v in raw_config.items()
                if k
                not in [
                    "provider",
                    "model",
                    "api_key_file",
                    "auth_token_file",
                    "base_url_file",
                    "base_url_env",
                    "api_config",
                ]
            },
        )

    def _resolve_sensitive_value(self, config: dict[str, Any], field_name: str) -> str | None:
        """
        Resolve a sensitive value from config with env override.

        Precedence:
        1) Explicit env var (e.g., OPENAI_API_KEY)
        2) File path from <field_name>_file in config
        3) Bare value in config (fallback)

        Args:
            config: Loaded config dict
            field_name: Base field name (e.g., "api_key")

        Returns:
            Resolved value or None if not found
        """
        env_var_name = self._infer_env_var_name(config.get("provider"), field_name)

        # 1) Check env var first (highest priority)
        if env_var_name:
            env_value = os.getenv(env_var_name)
            if env_value:
                return env_value.strip()

        # 2) Check for _file field in config
        file_field = f"{field_name}_file"
        if file_field in config:
            file_path_str = config[file_field]
            if file_path_str:
                return self._read_secret_file(file_path_str)

        # 3) Check for bare value in config (for non-sensitive fields)
        if field_name in config:
            value = config[field_name]
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    def _read_secret_file(self, file_path: str) -> str:
        """
        Read a secret from a file (relative to config dir).

        Args:
            file_path: Relative path (from config dir) or absolute path

        Returns:
            Stripped file contents

        Raises:
            ConfigError: If file cannot be read
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.config_dir / path

        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError as e:
            # Don't expose the full path or the actual error details which might contain secrets
            raise ConfigError("Failed to read secret file: permission denied or file not found") from e

    def _infer_env_var_name(self, provider: str | None, field_name: str) -> str | None:
        """
        Infer standard env var name for a provider + field.

        Args:
            provider: Provider name
            field_name: Field name (e.g., "api_key")

        Returns:
            Env var name or None
        """
        if not provider:
            return None

        # Standard mappings
        if provider == "openai" and field_name == "api_key":
            return "OPENAI_API_KEY"
        if provider == "anthropic" and field_name == "api_key":
            return "ANTHROPIC_API_KEY"
        if provider == "ollama" and field_name == "base_url":
            return "OLLAMA_HOST"

        # Generic fallback: PROVIDER_FIELD
        return f"{provider.upper()}_{field_name.upper()}"

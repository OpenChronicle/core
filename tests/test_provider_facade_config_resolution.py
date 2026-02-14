"""Tests for config-driven ProviderAwareLLMFacade resolution semantics."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from openchronicle.core.application.config.model_config import ModelConfigLoader, ResolvedModelConfig
from openchronicle.core.domain.ports.llm_port import LLMPort, LLMResponse, LLMUsage
from openchronicle.core.infrastructure.llm.provider_facade import ProviderAwareLLMFacade


class RecordingAdapter(LLMPort):
    """Adapter that records the resolved config used to build it."""

    def __init__(self, cfg_model: str) -> None:
        self.cfg_model = cfg_model
        self.calls: list[str] = []

    async def complete_async(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.calls.append(model)
        return LLMResponse(
            provider=str(provider or "unknown"),
            model=model,
            content=model,
            finish_reason="stop",
            usage=LLMUsage(input_tokens=0, output_tokens=0, total_tokens=0),
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Synchronous completion (not implemented)."""
        raise NotImplementedError("Use complete_async")


@pytest.mark.asyncio
async def test_facade_resolves_per_model_without_provider_sticking() -> None:
    """Multiple models for the same provider should each resolve and cache separately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        (models_dir / "model_a.json").write_text(
            """
{"provider": "openai", "model": "model-a", "api_config": {"api_key": "key-a", "auth_format": "Bearer {api_key}", "auth_header": "Authorization"}}
""",
            encoding="utf-8",
        )
        (models_dir / "model_b.json").write_text(
            """
{"provider": "openai", "model": "model-b", "api_config": {"api_key": "key-b", "auth_format": "Bearer {api_key}", "auth_header": "Authorization"}}
""",
            encoding="utf-8",
        )

        loader = ModelConfigLoader(tmpdir)

        created: list[str] = []

        def factory(cfg: ResolvedModelConfig) -> RecordingAdapter:
            created.append(cfg.model)
            return RecordingAdapter(cfg.model)

        facade = ProviderAwareLLMFacade(
            config_loader=loader,
            adapter_factories={"openai": factory},
            default_provider=None,
        )

        await facade.complete_async(messages=[{"role": "user", "content": "hi"}], model="model-a", provider="openai")
        await facade.complete_async(messages=[{"role": "user", "content": "hi"}], model="model-b", provider="openai")

        assert created == ["model-a", "model-b"]
        assert len(facade._adapter_cache) == 2  # per (provider, model)


@pytest.mark.asyncio
async def test_facade_allows_config_without_api_key_when_not_required() -> None:
    """Providers without auth requirements should resolve even when api_key is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        models_dir = Path(tmpdir) / "models"
        models_dir.mkdir(parents=True)

        (models_dir / "ollama.json").write_text(
            """
{"provider": "ollama", "model": "mixtral", "api_config": {}}
""",
            encoding="utf-8",
        )

        loader = ModelConfigLoader(tmpdir)
        captured_models: list[str] = []

        def factory(cfg: ResolvedModelConfig) -> RecordingAdapter:
            captured_models.append(cfg.model)
            return RecordingAdapter(cfg.model)

        facade = ProviderAwareLLMFacade(
            config_loader=loader,
            adapter_factories={"ollama": factory},
            default_provider=None,
        )

        result = await facade.complete_async(
            messages=[{"role": "user", "content": "hi"}],
            model="mixtral",
            provider="ollama",
        )

        assert result.model == "mixtral"
        assert captured_models == ["mixtral"]
        assert len(facade._adapter_cache) == 1

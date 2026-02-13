"""Tests for provider registry data integrity."""

from __future__ import annotations

import pytest

from openchronicle.core.application.config.provider_registry import (
    PROVIDERS,
    get_provider,
    list_providers,
    provider_names,
)

VALID_POOL_HINTS = {"fast", "quality", "both"}


class TestRegistryData:
    """Every provider and model has valid, complete data."""

    @pytest.mark.parametrize("name", list(PROVIDERS.keys()))
    def test_provider_has_required_fields(self, name: str) -> None:
        p = PROVIDERS[name]
        assert p.name, "name must be non-empty"
        assert p.display_name, "display_name must be non-empty"
        assert p.endpoint, "endpoint must be non-empty"
        assert p.adapter_provider, "adapter_provider must be non-empty"
        assert len(p.models) >= 1, "must have at least one model"
        assert p.default_timeout > 0, "default_timeout must be positive"

    @pytest.mark.parametrize("name", list(PROVIDERS.keys()))
    def test_models_have_valid_pool_hints(self, name: str) -> None:
        for m in PROVIDERS[name].models:
            assert m.pool_hint in VALID_POOL_HINTS, f"{name}/{m.model_id}: invalid pool_hint {m.pool_hint!r}"

    @pytest.mark.parametrize("name", list(PROVIDERS.keys()))
    def test_no_duplicate_model_ids(self, name: str) -> None:
        ids = [m.model_id for m in PROVIDERS[name].models]
        assert len(ids) == len(set(ids)), f"{name}: duplicate model IDs"

    @pytest.mark.parametrize("name", list(PROVIDERS.keys()))
    def test_models_have_required_fields(self, name: str) -> None:
        for m in PROVIDERS[name].models:
            assert m.model_id, f"{name}: model_id must be non-empty"
            assert m.display_name, f"{name}: display_name must be non-empty"
            assert m.description, f"{name}: description must be non-empty"

    def test_providers_requiring_key_have_env_var(self) -> None:
        for name, p in PROVIDERS.items():
            if p.requires_api_key:
                assert p.api_key_env, f"{name}: requires_api_key but no api_key_env"


class TestProviderSpecifics:
    """Provider-specific invariants from the plan."""

    def test_xai_uses_openai_adapter(self) -> None:
        xai = PROVIDERS["xai"]
        assert xai.adapter_provider == "openai"

    def test_ollama_no_key_required(self) -> None:
        ollama = PROVIDERS["ollama"]
        assert ollama.requires_api_key is False
        assert ollama.api_key_env is None

    def test_gemini_no_auth_header(self) -> None:
        gemini = PROVIDERS["gemini"]
        assert gemini.auth_header is None
        assert gemini.auth_format is None


class TestHelperFunctions:
    def test_list_providers_returns_all(self) -> None:
        result = list_providers()
        assert len(result) == len(PROVIDERS)

    def test_get_provider_known(self) -> None:
        p = get_provider("openai")
        assert p is not None
        assert p.name == "openai"

    def test_get_provider_unknown(self) -> None:
        assert get_provider("nonexistent") is None

    def test_provider_names(self) -> None:
        names = provider_names()
        assert set(names) == set(PROVIDERS.keys())

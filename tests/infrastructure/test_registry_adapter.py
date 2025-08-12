"""Tests for RegistryAdapter basic behaviors.

Focus: ensure discover_providers returns a dict structure and get_provider_config handles missing provider gracefully.
"""
from typing import Any

from openchronicle.infrastructure.persistence_adapters.registry_adapter import RegistryAdapter


def test_discover_providers_structure():
    adapter = RegistryAdapter()
    providers = adapter.discover_providers()
    # Should always return a dict
    assert isinstance(providers, dict)
    # Keys (if any) should be strings; values lists of dicts
    for name, models in providers.items():
        assert isinstance(name, str)
        assert isinstance(models, list)
        for m in models:
            assert isinstance(m, dict)


def test_get_provider_config_missing():
    adapter = RegistryAdapter()
    assert adapter.get_provider_config("__nonexistent_provider__") is None

"""Provider classification policy — determines whether an LLM provider is external."""

from __future__ import annotations

_LOCAL_PROVIDERS = {"ollama", "stub"}


def is_external_provider(provider: str) -> bool:
    """Return True if the provider sends data to an external API."""
    return provider.strip().lower() not in _LOCAL_PROVIDERS

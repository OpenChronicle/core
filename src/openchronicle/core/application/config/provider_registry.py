"""Registry of known LLM providers and their models.

Pure data module — no I/O, no side effects. Used by the provider setup
service and CLI to generate model config files.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelDefinition:
    """A model offered by a provider."""

    model_id: str
    display_name: str
    description: str
    pool_hint: str  # "fast" | "quality" | "both"
    timeout: int | None = None  # override provider default, or None


@dataclass(frozen=True)
class ProviderDefinition:
    """Everything needed to generate config files for a provider."""

    name: str  # registry key, e.g. "xai"
    display_name: str  # e.g. "xAI (Grok)"
    adapter_provider: str  # JSON "provider" field (xai -> "openai")
    api_key_env: str | None  # standard env var, e.g. "XAI_API_KEY"
    requires_api_key: bool
    endpoint: str
    base_url: str | None
    auth_header: str | None
    auth_format: str | None
    default_timeout: int
    models: tuple[ModelDefinition, ...]


PROVIDERS: dict[str, ProviderDefinition] = {
    "openai": ProviderDefinition(
        name="openai",
        display_name="OpenAI",
        adapter_provider="openai",
        api_key_env="OPENAI_API_KEY",
        requires_api_key=True,
        endpoint="https://api.openai.com/v1/chat/completions",
        base_url="https://api.openai.com/v1",
        auth_header="Authorization",
        auth_format="Bearer {api_key}",
        default_timeout=30,
        models=(
            ModelDefinition("gpt-4o-mini", "GPT-4o Mini", "Fast and cost-effective", "fast"),
            ModelDefinition("gpt-4o", "GPT-4o", "Strong general-purpose reasoning", "quality"),
            ModelDefinition("o4-mini", "o4 Mini", "Reasoning model (compact)", "quality"),
        ),
    ),
    "anthropic": ProviderDefinition(
        name="anthropic",
        display_name="Anthropic",
        adapter_provider="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        requires_api_key=True,
        endpoint="https://api.anthropic.com/v1/messages",
        base_url="https://api.anthropic.com",
        auth_header="x-api-key",
        auth_format="{api_key}",
        default_timeout=60,
        models=(
            ModelDefinition("claude-sonnet-4-20250514", "Claude Sonnet 4", "Strong reasoning and writing", "quality"),
            ModelDefinition("claude-haiku-4-5-20251001", "Claude Haiku 4.5", "Fast and cost-effective", "fast"),
        ),
    ),
    "gemini": ProviderDefinition(
        name="gemini",
        display_name="Google Gemini",
        adapter_provider="gemini",
        api_key_env="GEMINI_API_KEY",
        requires_api_key=True,
        endpoint="https://generativelanguage.googleapis.com/v1beta",
        base_url=None,
        auth_header=None,
        auth_format=None,
        default_timeout=30,
        models=(
            ModelDefinition("gemini-2.0-flash", "Gemini 2.0 Flash", "Fast and capable", "fast"),
            ModelDefinition("gemini-2.5-flash", "Gemini 2.5 Flash", "Next-gen fast model", "fast"),
            ModelDefinition("gemini-2.5-pro", "Gemini 2.5 Pro", "Advanced reasoning", "quality"),
        ),
    ),
    "groq": ProviderDefinition(
        name="groq",
        display_name="Groq",
        adapter_provider="groq",
        api_key_env="GROQ_API_KEY",
        requires_api_key=True,
        endpoint="https://api.groq.com/openai/v1/chat/completions",
        base_url="https://api.groq.com/openai/v1",
        auth_header="Authorization",
        auth_format="Bearer {api_key}",
        default_timeout=30,
        models=(ModelDefinition("llama-3.3-70b-versatile", "Llama 3.3 70B", "Fast inference via Groq", "fast"),),
    ),
    "ollama": ProviderDefinition(
        name="ollama",
        display_name="Ollama (local)",
        adapter_provider="ollama",
        api_key_env=None,
        requires_api_key=False,
        endpoint="http://localhost:11434/api/chat",
        base_url="http://localhost:11434",
        auth_header=None,
        auth_format=None,
        default_timeout=120,
        models=(
            ModelDefinition("llama3.1:8b", "Llama 3.1 8B", "General purpose local model", "fast"),
            ModelDefinition("mistral:7b", "Mistral 7B", "Local Mistral model", "fast"),
            ModelDefinition("qwen2.5:7b", "Qwen 2.5 7B", "Local Qwen model", "fast"),
        ),
    ),
    "xai": ProviderDefinition(
        name="xai",
        display_name="xAI (Grok)",
        adapter_provider="openai",  # OpenAI-compatible API
        api_key_env="XAI_API_KEY",
        requires_api_key=True,
        endpoint="https://api.x.ai/v1/chat/completions",
        base_url="https://api.x.ai/v1",
        auth_header="Authorization",
        auth_format="Bearer {api_key}",
        default_timeout=60,
        models=(
            ModelDefinition("grok-3", "Grok 3", "xAI's flagship model", "quality"),
            ModelDefinition("grok-3-mini", "Grok 3 Mini", "Fast and efficient", "fast"),
        ),
    ),
}


def list_providers() -> list[ProviderDefinition]:
    """All known providers, in registry order."""
    return list(PROVIDERS.values())


def get_provider(name: str) -> ProviderDefinition | None:
    """Look up a provider by registry name."""
    return PROVIDERS.get(name)


def provider_names() -> list[str]:
    """All known provider names."""
    return list(PROVIDERS.keys())

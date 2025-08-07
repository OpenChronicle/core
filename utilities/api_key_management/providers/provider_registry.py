"""
Provider registry implementation for managing AI provider configurations.

This module manages provider configurations, aliases, and validation patterns
from the model registry and built-in provider definitions.
"""

from typing import Optional, List, Dict, Any
import json
import sys
from pathlib import Path

# Add utilities to path for logging
sys.path.append(str(Path(__file__).parent.parent.parent))
try:
    from logging_system import log_error, log_info
except ImportError:
    # Fallback logging if logging_system not available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    def log_info(msg): logger.info(msg)
    def log_error(msg): logger.error(msg)

from ..interfaces.api_key_interfaces import IProviderRegistry, ProviderConfig

# Built-in provider configurations
BUILT_IN_PROVIDERS = {
    "openai": ProviderConfig(
        name="openai",
        display_name="OpenAI",
        keyring_username="openai_api_key",
        api_key_pattern=r"^sk-[A-Za-z0-9]{48}$",
        setup_url="https://platform.openai.com/api-keys",
        description="OpenAI API key for GPT models",
        aliases=[]
    ),
    "anthropic": ProviderConfig(
        name="anthropic",
        display_name="Anthropic Claude",
        keyring_username="anthropic_api_key",
        api_key_pattern=r"^sk-ant-[A-Za-z0-9\-_]{95}$",
        setup_url="https://console.anthropic.com/account/keys",
        description="Anthropic Claude API key",
        aliases=[]
    ),
    "google": ProviderConfig(
        name="google",
        display_name="Google Gemini",
        keyring_username="google_api_key",
        api_key_pattern=r"^AI[A-Za-z0-9\-_]{35}$",
        setup_url="https://makersuite.google.com/app/apikey",
        description="Google Gemini API key",
        aliases=["gemini"]
    ),
    "groq": ProviderConfig(
        name="groq",
        display_name="Groq",
        keyring_username="groq_api_key",
        api_key_pattern=r"^gsk_[A-Za-z0-9]{52}$",
        setup_url="https://console.groq.com/keys",
        description="Groq API key for fast inference",
        aliases=[]
    ),
    "cohere": ProviderConfig(
        name="cohere",
        display_name="Cohere",
        keyring_username="cohere_api_key",
        api_key_pattern=None,  # Pattern varies
        setup_url="https://dashboard.cohere.com/api-keys",
        description="Cohere API key",
        aliases=[]
    ),
    "mistral": ProviderConfig(
        name="mistral",
        display_name="Mistral",
        keyring_username="mistral_api_key",
        api_key_pattern=None,  # Pattern varies
        setup_url="https://console.mistral.ai/api-keys/",
        description="Mistral API key",
        aliases=[]
    ),
    "huggingface": ProviderConfig(
        name="huggingface",
        display_name="Hugging Face",
        keyring_username="huggingface_api_key",
        api_key_pattern=r"^hf_[A-Za-z0-9]{37}$",
        setup_url="https://huggingface.co/settings/tokens",
        description="Hugging Face API token",
        aliases=["hf"]
    ),
    "azure": ProviderConfig(
        name="azure",
        display_name="Azure OpenAI",
        keyring_username="azure_openai_api_key",
        api_key_pattern=None,  # Azure keys vary in format
        setup_url="https://portal.azure.com/",
        description="Azure OpenAI API key",
        aliases=["azure_openai"]
    )
}

# Provider alias mapping
PROVIDER_ALIASES = {
    "gemini": "google",
    "azure_openai": "azure",
    "hf": "huggingface"
}


class ProviderRegistry(IProviderRegistry):
    """Production provider registry with model registry integration."""
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize provider registry.
        
        Args:
            registry_path: Path to model registry JSON file
        """
        self._registry_path = registry_path or self._get_default_registry_path()
        self._providers = BUILT_IN_PROVIDERS.copy()
        self._load_from_model_registry()
    
    def _get_default_registry_path(self) -> Path:
        """Get default path to model registry."""
        return Path(__file__).parent.parent.parent.parent / "config" / "model_registry.json"
    
    def _load_from_model_registry(self) -> None:
        """Load additional provider configurations from model registry."""
        try:
            if not self._registry_path.exists():
                log_info(f"Model registry not found at {self._registry_path}, using built-in providers only")
                return
            
            with open(self._registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            providers = registry.get("environment_config", {}).get("providers", {})
            
            for provider_name, provider_config in providers.items():
                validation = provider_config.get("validation", {})
                
                if validation.get("requires_api_key"):
                    # Update existing provider or create new one
                    existing = self._providers.get(provider_name.lower())
                    
                    config = ProviderConfig(
                        name=provider_name.lower(),
                        display_name=validation.get("service_name", provider_name.title()),
                        keyring_username=f"{provider_name.lower()}_api_key",
                        api_key_pattern=validation.get("api_key_format"),
                        setup_url=validation.get("setup_url", ""),
                        description=validation.get("description", f"{provider_name} API key"),
                        aliases=existing.aliases if existing else []
                    )
                    
                    self._providers[provider_name.lower()] = config
            
            log_info(f"Loaded provider configurations from model registry: {len(self._providers)} providers")
            
        except Exception as e:
            log_error(f"Failed to load provider configurations from model registry: {e}")
    
    def get_provider_config(self, provider: str) -> Optional[ProviderConfig]:
        """
        Get configuration for a provider.
        
        Args:
            provider: Provider name or alias
            
        Returns:
            ProviderConfig or None if not found
        """
        # Resolve alias first
        resolved_provider = self.resolve_provider_alias(provider)
        return self._providers.get(resolved_provider.lower())
    
    def get_all_providers(self) -> List[ProviderConfig]:
        """
        Get all supported provider configurations.
        
        Returns:
            List of all ProviderConfig objects
        """
        return list(self._providers.values())
    
    def resolve_provider_alias(self, provider: str) -> str:
        """
        Resolve provider alias to main provider name.
        
        Args:
            provider: Provider name or alias
            
        Returns:
            Main provider name
        """
        provider_lower = provider.lower()
        
        # Check built-in aliases first
        if provider_lower in PROVIDER_ALIASES:
            return PROVIDER_ALIASES[provider_lower]
        
        # Check provider-specific aliases
        for config in self._providers.values():
            if config.aliases and provider_lower in config.aliases:
                return config.name
        
        return provider_lower
    
    def load_validation_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Load API key validation patterns from provider configurations.
        
        Returns:
            Dictionary with provider validation patterns
        """
        patterns = {}
        
        for provider_name, config in self._providers.items():
            if config.api_key_pattern:
                patterns[provider_name] = {
                    "pattern": config.api_key_pattern,
                    "service_name": config.display_name,
                    "setup_url": config.setup_url,
                    "description": config.description
                }
        
        return patterns
    
    def add_provider(self, config: ProviderConfig) -> None:
        """
        Add or update a provider configuration.
        
        Args:
            config: Provider configuration to add
        """
        self._providers[config.name.lower()] = config
        log_info(f"Added/updated provider configuration: {config.name}")
    
    def remove_provider(self, provider: str) -> bool:
        """
        Remove a provider configuration.
        
        Args:
            provider: Provider name to remove
            
        Returns:
            True if removed, False if not found
        """
        provider_lower = provider.lower()
        if provider_lower in self._providers:
            del self._providers[provider_lower]
            log_info(f"Removed provider configuration: {provider}")
            return True
        return False


class StaticProviderRegistry(IProviderRegistry):
    """Static provider registry using only built-in configurations."""
    
    def __init__(self):
        """Initialize static registry with built-in providers."""
        self._providers = BUILT_IN_PROVIDERS.copy()
    
    def get_provider_config(self, provider: str) -> Optional[ProviderConfig]:
        """Get configuration for a provider."""
        resolved_provider = self.resolve_provider_alias(provider)
        return self._providers.get(resolved_provider.lower())
    
    def get_all_providers(self) -> List[ProviderConfig]:
        """Get all supported provider configurations."""
        return list(self._providers.values())
    
    def resolve_provider_alias(self, provider: str) -> str:
        """Resolve provider alias to main provider name."""
        provider_lower = provider.lower()
        
        # Check built-in aliases
        if provider_lower in PROVIDER_ALIASES:
            return PROVIDER_ALIASES[provider_lower]
        
        # Check provider-specific aliases
        for config in self._providers.values():
            if config.aliases and provider_lower in config.aliases:
                return config.name
        
        return provider_lower
    
    def load_validation_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load API key validation patterns from built-in configurations."""
        patterns = {}
        
        for provider_name, config in self._providers.items():
            if config.api_key_pattern:
                patterns[provider_name] = {
                    "pattern": config.api_key_pattern,
                    "service_name": config.display_name,
                    "setup_url": config.setup_url,
                    "description": config.description
                }
        
        return patterns


def create_provider_registry(registry_path: Optional[Path] = None) -> IProviderRegistry:
    """
    Factory function to create provider registry.
    
    Args:
        registry_path: Optional path to model registry JSON file
        
    Returns:
        ProviderRegistry instance
    """
    return ProviderRegistry(registry_path)


def create_static_provider_registry() -> IProviderRegistry:
    """
    Factory function to create static provider registry.
    
    Returns:
        StaticProviderRegistry instance
    """
    return StaticProviderRegistry()


def create_mock_provider_registry() -> IProviderRegistry:
    """
    Factory function to create mock provider registry for testing.
    
    Returns:
        MockProviderRegistry instance
    """
    from ..interfaces.api_key_interfaces import MockProviderRegistry
    return MockProviderRegistry()

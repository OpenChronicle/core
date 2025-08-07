"""
Interfaces for the API key management system.

This module defines the core interfaces that provide clean separation of concerns
for API key management operations following SOLID principles.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class ApiKeyInfo:
    """Information about a stored API key."""
    provider: str
    masked_key: str  # Only show first/last few characters
    stored_date: Optional[datetime] = None
    is_valid_format: bool = True
    validation_message: str = ""


@dataclass
class ValidationResult:
    """Result of API key format validation."""
    valid: bool
    reason: str
    expected_pattern: Optional[str] = None
    setup_url: Optional[str] = None
    suggestion: Optional[str] = None
    pattern: Optional[str] = None


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    name: str
    display_name: str
    keyring_username: str
    api_key_pattern: Optional[str] = None
    setup_url: Optional[str] = None
    description: Optional[str] = None
    aliases: List[str] = None


@dataclass
class KeyringInfo:
    """Information about the keyring backend."""
    available: bool
    backend_name: Optional[str] = None
    service_name: Optional[str] = None
    reason: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class StorageResult:
    """Result of a storage operation."""
    success: bool
    message: str
    error_details: Optional[str] = None


class IKeyringBackend(ABC):
    """Interface for OS keyring integration."""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if keyring is available for secure storage."""
        pass
    
    @abstractmethod
    def get_keyring_info(self) -> KeyringInfo:
        """Get information about the keyring backend."""
        pass
    
    @abstractmethod
    def get_password(self, service: str, username: str) -> Optional[str]:
        """Retrieve password from keyring."""
        pass
    
    @abstractmethod
    def set_password(self, service: str, username: str, password: str) -> bool:
        """Store password in keyring."""
        pass
    
    @abstractmethod
    def delete_password(self, service: str, username: str) -> bool:
        """Delete password from keyring."""
        pass


class IProviderRegistry(ABC):
    """Interface for managing provider configurations."""
    
    @abstractmethod
    def get_provider_config(self, provider: str) -> Optional[ProviderConfig]:
        """Get configuration for a provider."""
        pass
    
    @abstractmethod
    def get_all_providers(self) -> List[ProviderConfig]:
        """Get all supported provider configurations."""
        pass
    
    @abstractmethod
    def resolve_provider_alias(self, provider: str) -> str:
        """Resolve provider alias to main provider name."""
        pass
    
    @abstractmethod
    def load_validation_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load API key validation patterns from model registry."""
        pass


class IApiKeyValidator(ABC):
    """Interface for API key format validation."""
    
    @abstractmethod
    def validate_format(self, provider: str, api_key: str) -> ValidationResult:
        """Validate API key format against provider patterns."""
        pass
    
    @abstractmethod
    def get_validation_info(self, provider: str) -> Dict[str, Any]:
        """Get validation information for a provider."""
        pass


class IApiKeyStorage(ABC):
    """Interface for API key storage operations."""
    
    @abstractmethod
    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve API key for a provider."""
        pass
    
    @abstractmethod
    def set_api_key(self, provider: str, api_key: str) -> StorageResult:
        """Store API key for a provider."""
        pass
    
    @abstractmethod
    def remove_api_key(self, provider: str) -> StorageResult:
        """Remove API key for a provider."""
        pass
    
    @abstractmethod
    def list_stored_keys(self) -> List[ApiKeyInfo]:
        """List all stored API keys with metadata."""
        pass
    
    @abstractmethod
    def has_api_key(self, provider: str) -> bool:
        """Check if API key exists for provider."""
        pass
    
    @abstractmethod
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass


class IUserInterface(ABC):
    """Interface for user interactions."""
    
    @abstractmethod
    def prompt_for_api_key(self, provider: str, config: ProviderConfig) -> Optional[str]:
        """Securely prompt user for API key."""
        pass
    
    @abstractmethod
    def show_validation_error(self, result: ValidationResult, provider: str) -> bool:
        """Show validation error and ask if user wants to continue."""
        pass
    
    @abstractmethod
    def show_success_message(self, provider: str, operation: str, details: str = "") -> None:
        """Show success message to user."""
        pass
    
    @abstractmethod
    def show_error_message(self, message: str, details: str = "") -> None:
        """Show error message to user."""
        pass
    
    @abstractmethod
    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Ask user to confirm an action."""
        pass


class IApiKeyOrchestrator(ABC):
    """Interface for coordinating API key management operations."""
    
    @abstractmethod
    def setup_api_key(self, provider: str, interactive: bool = True) -> StorageResult:
        """Set up API key for a provider with validation and user interaction."""
        pass
    
    @abstractmethod
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider."""
        pass
    
    @abstractmethod
    def remove_api_key(self, provider: str) -> StorageResult:
        """Remove API key for a provider."""
        pass
    
    @abstractmethod
    def list_api_keys(self) -> List[ApiKeyInfo]:
        """List all stored API keys with metadata."""
        pass
    
    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information including keyring backend."""
        pass
    
    @abstractmethod
    def validate_api_key(self, provider: str, api_key: str) -> ValidationResult:
        """Validate API key format for a provider."""
        pass


# Mock implementations for testing

class MockKeyringBackend(IKeyringBackend):
    """Mock keyring backend for testing."""
    
    def __init__(self, available: bool = True):
        self._available = available
        self._storage: Dict[str, Dict[str, str]] = {}
    
    def is_available(self) -> bool:
        return self._available
    
    def get_keyring_info(self) -> KeyringInfo:
        return KeyringInfo(
            available=self._available,
            backend_name="MockKeyring" if self._available else None,
            service_name="openchronicle",
            reason=None if self._available else "Mock keyring not available",
            recommendation=None if self._available else "Install keyring library"
        )
    
    def get_password(self, service: str, username: str) -> Optional[str]:
        if not self._available:
            return None
        return self._storage.get(service, {}).get(username)
    
    def set_password(self, service: str, username: str, password: str) -> bool:
        if not self._available:
            return False
        if service not in self._storage:
            self._storage[service] = {}
        self._storage[service][username] = password
        return True
    
    def delete_password(self, service: str, username: str) -> bool:
        if not self._available:
            return False
        if service in self._storage and username in self._storage[service]:
            del self._storage[service][username]
            return True
        return False


class MockProviderRegistry(IProviderRegistry):
    """Mock provider registry for testing."""
    
    def __init__(self):
        self._providers = {
            "openai": ProviderConfig(
                name="openai",
                display_name="OpenAI",
                keyring_username="openai_api_key",
                api_key_pattern=r"^sk-[A-Za-z0-9]{48}$",
                setup_url="https://platform.openai.com/api-keys",
                description="OpenAI API key",
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
            )
        }
    
    def get_provider_config(self, provider: str) -> Optional[ProviderConfig]:
        return self._providers.get(provider.lower())
    
    def get_all_providers(self) -> List[ProviderConfig]:
        return list(self._providers.values())
    
    def resolve_provider_alias(self, provider: str) -> str:
        # Simple alias resolution
        aliases = {"gemini": "google", "azure": "openai"}
        return aliases.get(provider.lower(), provider.lower())
    
    def load_validation_patterns(self) -> Dict[str, Dict[str, Any]]:
        return {
            provider: {
                "pattern": config.api_key_pattern,
                "service_name": config.display_name,
                "setup_url": config.setup_url,
                "description": config.description
            }
            for provider, config in self._providers.items()
            if config.api_key_pattern
        }


class MockApiKeyValidator(IApiKeyValidator):
    """Mock API key validator for testing."""
    
    def __init__(self, provider_registry: IProviderRegistry):
        self._provider_registry = provider_registry
    
    def validate_format(self, provider: str, api_key: str) -> ValidationResult:
        config = self._provider_registry.get_provider_config(provider)
        if not config or not config.api_key_pattern:
            return ValidationResult(
                valid=len(api_key) >= 10,
                reason="No validation pattern available" if len(api_key) >= 10 else "API key too short"
            )
        
        import re
        if re.match(config.api_key_pattern, api_key):
            return ValidationResult(valid=True, reason=f"Valid {config.display_name} API key format")
        else:
            return ValidationResult(
                valid=False,
                reason=f"Invalid {config.display_name} API key format",
                expected_pattern=config.api_key_pattern,
                setup_url=config.setup_url
            )
    
    def get_validation_info(self, provider: str) -> Dict[str, Any]:
        config = self._provider_registry.get_provider_config(provider)
        if not config:
            return {}
        return {
            "pattern": config.api_key_pattern,
            "setup_url": config.setup_url,
            "description": config.description
        }


class MockUserInterface(IUserInterface):
    """Mock user interface for testing."""
    
    def __init__(self):
        self._responses = {}
        self._prompts = []
    
    def set_api_key_response(self, provider: str, api_key: str):
        """Set mock response for API key prompt."""
        self._responses[f"api_key_{provider}"] = api_key
    
    def set_confirm_response(self, message: str, response: bool):
        """Set mock response for confirmation."""
        self._responses[f"confirm_{message}"] = response
    
    def prompt_for_api_key(self, provider: str, config: ProviderConfig) -> Optional[str]:
        self._prompts.append(f"prompt_api_key_{provider}")
        return self._responses.get(f"api_key_{provider}")
    
    def show_validation_error(self, result: ValidationResult, provider: str) -> bool:
        self._prompts.append(f"validation_error_{provider}")
        return self._responses.get(f"confirm_validation_error_{provider}", False)
    
    def show_success_message(self, provider: str, operation: str, details: str = "") -> None:
        self._prompts.append(f"success_{operation}_{provider}")
    
    def show_error_message(self, message: str, details: str = "") -> None:
        self._prompts.append(f"error_{message}")
    
    def confirm_action(self, message: str, default: bool = False) -> bool:
        self._prompts.append(f"confirm_{message}")
        return self._responses.get(f"confirm_{message}", default)
    
    @property
    def prompts(self) -> List[str]:
        """Get list of prompts shown to user."""
        return self._prompts.copy()

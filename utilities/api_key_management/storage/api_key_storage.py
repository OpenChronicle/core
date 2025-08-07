"""
API key storage implementation for secure key management.

This module provides secure API key storage operations using the keyring
backend with metadata tracking and error handling.
"""

from typing import Optional, List
from datetime import datetime
import sys
from pathlib import Path

# Add utilities to path for logging
sys.path.append(str(Path(__file__).parent.parent.parent))
try:
    from logging_system import log_info, log_error, log_system_event
except ImportError:
    # Fallback logging if logging_system not available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    def log_info(msg): logger.info(msg)
    def log_error(msg): logger.error(msg)
    def log_system_event(event, msg): logger.info(f"{event}: {msg}")

from ..interfaces.api_key_interfaces import (
    IApiKeyStorage, IKeyringBackend, IProviderRegistry, IApiKeyValidator,
    ApiKeyInfo, StorageResult
)


class ApiKeyStorage(IApiKeyStorage):
    """Production API key storage with secure keyring backend."""
    
    def __init__(
        self,
        keyring_backend: IKeyringBackend,
        provider_registry: IProviderRegistry,
        validator: Optional[IApiKeyValidator] = None,
        service_name: str = "openchronicle"
    ):
        """
        Initialize API key storage.
        
        Args:
            keyring_backend: Keyring backend for secure storage
            provider_registry: Provider registry for configurations
            validator: Optional validator for format checking
            service_name: Service name for keyring storage
        """
        self._keyring = keyring_backend
        self._provider_registry = provider_registry
        self._validator = validator
        self._service_name = service_name
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Retrieve API key for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            API key or None if not found/not available
        """
        if not self._keyring.is_available():
            return None
        
        # Resolve provider alias and get configuration
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        config = self._provider_registry.get_provider_config(resolved_provider)
        
        if not config:
            # Use fallback username format
            username = f"{resolved_provider.lower()}_api_key"
        else:
            username = config.keyring_username
        
        api_key = self._keyring.get_password(self._service_name, username)
        
        if api_key:
            log_info(f"Retrieved API key for {provider} from secure storage")
        
        return api_key
    
    def set_api_key(self, provider: str, api_key: str) -> StorageResult:
        """
        Store API key for a provider.
        
        Args:
            provider: Provider name
            api_key: API key to store
            
        Returns:
            StorageResult with operation outcome
        """
        if not self._keyring.is_available():
            return StorageResult(
                success=False,
                message="Keyring not available for secure storage",
                error_details="Install keyring library for secure storage: pip install keyring"
            )
        
        if not api_key or not api_key.strip():
            return StorageResult(
                success=False,
                message="API key is empty",
                error_details="Please provide a valid API key"
            )
        
        api_key = api_key.strip()
        
        # Resolve provider and get configuration
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        config = self._provider_registry.get_provider_config(resolved_provider)
        
        if not config:
            # Use fallback username format
            username = f"{resolved_provider.lower()}_api_key"
            display_name = resolved_provider.title()
        else:
            username = config.keyring_username
            display_name = config.display_name
        
        # Validate format if validator is available
        if self._validator:
            validation_result = self._validator.validate_format(resolved_provider, api_key)
            if not validation_result.valid:
                return StorageResult(
                    success=False,
                    message=f"Invalid API key format for {display_name}",
                    error_details=validation_result.reason
                )
        
        # Store the key
        success = self._keyring.set_password(self._service_name, username, api_key)
        
        if success:
            log_system_event("api_key_stored", f"API key stored securely for {provider}")
            return StorageResult(
                success=True,
                message=f"API key stored securely for {display_name}"
            )
        else:
            return StorageResult(
                success=False,
                message=f"Failed to store API key for {display_name}",
                error_details="Keyring storage operation failed"
            )
    
    def remove_api_key(self, provider: str) -> StorageResult:
        """
        Remove API key for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            StorageResult with operation outcome
        """
        if not self._keyring.is_available():
            return StorageResult(
                success=False,
                message="Keyring not available",
                error_details="Cannot remove keys without keyring support"
            )
        
        # Resolve provider and get configuration
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        config = self._provider_registry.get_provider_config(resolved_provider)
        
        if not config:
            username = f"{resolved_provider.lower()}_api_key"
            display_name = resolved_provider.title()
        else:
            username = config.keyring_username
            display_name = config.display_name
        
        # Check if key exists
        if not self.has_api_key(provider):
            return StorageResult(
                success=False,
                message=f"No API key found for {display_name}",
                error_details="Key does not exist in secure storage"
            )
        
        # Remove the key
        success = self._keyring.delete_password(self._service_name, username)
        
        if success:
            log_system_event("api_key_removed", f"API key removed for {provider}")
            return StorageResult(
                success=True,
                message=f"API key removed for {display_name}"
            )
        else:
            return StorageResult(
                success=False,
                message=f"Failed to remove API key for {display_name}",
                error_details="Keyring deletion operation failed"
            )
    
    def list_stored_keys(self) -> List[ApiKeyInfo]:
        """
        List all stored API keys with metadata.
        
        Returns:
            List of ApiKeyInfo objects
        """
        if not self._keyring.is_available():
            return []
        
        stored_keys = []
        
        # Check all known providers
        for config in self._provider_registry.get_all_providers():
            try:
                api_key = self._keyring.get_password(self._service_name, config.keyring_username)
                if api_key:
                    # Create masked version
                    masked_key = self._mask_api_key(api_key)
                    
                    # Validate format if validator is available
                    is_valid = True
                    validation_message = ""
                    if self._validator:
                        validation_result = self._validator.validate_format(config.name, api_key)
                        is_valid = validation_result.valid
                        validation_message = validation_result.reason
                    
                    stored_keys.append(ApiKeyInfo(
                        provider=config.name,
                        masked_key=masked_key,
                        stored_date=datetime.now(),  # We don't track actual storage date
                        is_valid_format=is_valid,
                        validation_message=validation_message
                    ))
            except Exception as e:
                log_error(f"Failed to check API key for {config.name}: {e}")
                continue
        
        return stored_keys
    
    def has_api_key(self, provider: str) -> bool:
        """
        Check if API key exists for provider.
        
        Args:
            provider: Provider name
            
        Returns:
            True if key exists, False otherwise
        """
        api_key = self.get_api_key(provider)
        return api_key is not None and len(api_key.strip()) > 0
    
    def _mask_api_key(self, api_key: str) -> str:
        """
        Create masked version of API key for display.
        
        Args:
            api_key: Original API key
            
        Returns:
            Masked API key string
        """
        if len(api_key) <= 8:
            return "*" * len(api_key)
        
        # Show first 4 and last 4 characters
        return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"
    
    def get_storage_stats(self) -> dict:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        keyring_info = self._keyring.get_keyring_info()
        stored_keys = self.list_stored_keys()
        
        return {
            "keyring_available": keyring_info.available,
            "keyring_backend": keyring_info.backend_name,
            "service_name": self._service_name,
            "total_stored_keys": len(stored_keys),
            "valid_keys": sum(1 for key in stored_keys if key.is_valid_format),
            "invalid_keys": sum(1 for key in stored_keys if not key.is_valid_format),
            "providers_with_keys": [key.provider for key in stored_keys]
        }


class MemoryApiKeyStorage(IApiKeyStorage):
    """In-memory API key storage for testing or temporary use."""
    
    def __init__(self, provider_registry: IProviderRegistry, validator: Optional[IApiKeyValidator] = None):
        """
        Initialize memory storage.
        
        Args:
            provider_registry: Provider registry for configurations
            validator: Optional validator for format checking
        """
        self._storage = {}
        self._provider_registry = provider_registry
        self._validator = validator
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve API key from memory storage."""
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        return self._storage.get(resolved_provider.lower())
    
    def set_api_key(self, provider: str, api_key: str) -> StorageResult:
        """Store API key in memory."""
        if not api_key or not api_key.strip():
            return StorageResult(
                success=False,
                message="API key is empty"
            )
        
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        config = self._provider_registry.get_provider_config(resolved_provider)
        display_name = config.display_name if config else resolved_provider.title()
        
        # Validate if validator available
        if self._validator:
            validation_result = self._validator.validate_format(resolved_provider, api_key.strip())
            if not validation_result.valid:
                return StorageResult(
                    success=False,
                    message=f"Invalid API key format for {display_name}",
                    error_details=validation_result.reason
                )
        
        self._storage[resolved_provider.lower()] = api_key.strip()
        return StorageResult(
            success=True,
            message=f"API key stored in memory for {display_name}"
        )
    
    def remove_api_key(self, provider: str) -> StorageResult:
        """Remove API key from memory."""
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        config = self._provider_registry.get_provider_config(resolved_provider)
        display_name = config.display_name if config else resolved_provider.title()
        
        if resolved_provider.lower() in self._storage:
            del self._storage[resolved_provider.lower()]
            return StorageResult(
                success=True,
                message=f"API key removed from memory for {display_name}"
            )
        else:
            return StorageResult(
                success=False,
                message=f"No API key found for {display_name}"
            )
    
    def list_stored_keys(self) -> List[ApiKeyInfo]:
        """List stored keys in memory."""
        stored_keys = []
        
        for provider, api_key in self._storage.items():
            config = self._provider_registry.get_provider_config(provider)
            display_name = config.display_name if config else provider.title()
            
            # Mask the key
            masked_key = f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}" if len(api_key) > 8 else "*" * len(api_key)
            
            # Validate if validator available
            is_valid = True
            validation_message = ""
            if self._validator:
                validation_result = self._validator.validate_format(provider, api_key)
                is_valid = validation_result.valid
                validation_message = validation_result.reason
            
            stored_keys.append(ApiKeyInfo(
                provider=provider,
                masked_key=masked_key,
                stored_date=datetime.now(),
                is_valid_format=is_valid,
                validation_message=validation_message
            ))
        
        return stored_keys
    
    def has_api_key(self, provider: str) -> bool:
        """Check if API key exists in memory."""
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        return resolved_provider.lower() in self._storage
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics for memory storage."""
        stored_keys = self.list_stored_keys()
        
        return {
            "keyring_available": False,
            "keyring_backend": "MemoryStorage",
            "service_name": "memory",
            "total_stored_keys": len(stored_keys),
            "valid_keys": sum(1 for key in stored_keys if key.is_valid_format),
            "invalid_keys": sum(1 for key in stored_keys if not key.is_valid_format),
            "providers_with_keys": [key.provider for key in stored_keys]
        }


def create_api_key_storage(
    keyring_backend: IKeyringBackend,
    provider_registry: IProviderRegistry,
    validator: Optional[IApiKeyValidator] = None,
    service_name: str = "openchronicle"
) -> IApiKeyStorage:
    """
    Factory function to create API key storage.
    
    Args:
        keyring_backend: Keyring backend for secure storage
        provider_registry: Provider registry for configurations
        validator: Optional validator for format checking
        service_name: Service name for keyring storage
        
    Returns:
        ApiKeyStorage instance
    """
    return ApiKeyStorage(keyring_backend, provider_registry, validator, service_name)


def create_memory_api_key_storage(
    provider_registry: IProviderRegistry,
    validator: Optional[IApiKeyValidator] = None
) -> IApiKeyStorage:
    """
    Factory function to create memory API key storage.
    
    Args:
        provider_registry: Provider registry for configurations
        validator: Optional validator for format checking
        
    Returns:
        MemoryApiKeyStorage instance
    """
    return MemoryApiKeyStorage(provider_registry, validator)

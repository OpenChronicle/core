"""
API key management orchestrator implementation.

This module coordinates all API key management components using dependency
injection to provide a unified interface for API key operations.
"""

from typing import Optional, List, Dict, Any
import sys
from pathlib import Path

# Add utilities to path for logging
sys.path.append(str(Path(__file__).parent.parent))
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

from .interfaces.api_key_interfaces import (
    IApiKeyOrchestrator, IKeyringBackend, IProviderRegistry, IApiKeyValidator,
    IApiKeyStorage, IUserInterface, ApiKeyInfo, StorageResult, ValidationResult
)


class ApiKeyOrchestrator(IApiKeyOrchestrator):
    """Production API key orchestrator with full dependency injection."""
    
    def __init__(
        self,
        keyring_backend: IKeyringBackend,
        provider_registry: IProviderRegistry,
        validator: IApiKeyValidator,
        storage: IApiKeyStorage,
        user_interface: IUserInterface
    ):
        """
        Initialize API key orchestrator.
        
        Args:
            keyring_backend: Keyring backend for secure storage
            provider_registry: Provider registry for configurations
            validator: API key validator for format checking
            storage: API key storage operations
            user_interface: User interface for interactions
        """
        self._keyring = keyring_backend
        self._provider_registry = provider_registry
        self._validator = validator
        self._storage = storage
        self._ui = user_interface
    
    def setup_api_key(self, provider: str, interactive: bool = True) -> StorageResult:
        """
        Set up API key for a provider with validation and user interaction.
        
        Args:
            provider: Provider name
            interactive: Whether to use interactive prompts
            
        Returns:
            StorageResult with operation outcome
        """
        if not self._keyring.is_available():
            error_msg = "Secure storage not available"
            error_details = "Install keyring library: pip install keyring"
            
            if interactive:
                self._ui.show_error_message(error_msg, error_details)
            
            return StorageResult(
                success=False,
                message=error_msg,
                error_details=error_details
            )
        
        # Resolve provider and get configuration
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        config = self._provider_registry.get_provider_config(resolved_provider)
        
        if not config:
            error_msg = f"Unsupported provider: {provider}"
            error_details = f"Supported providers: {', '.join([p.name for p in self._provider_registry.get_all_providers()])}"
            
            if interactive:
                self._ui.show_error_message(error_msg, error_details)
            
            return StorageResult(
                success=False,
                message=error_msg,
                error_details=error_details
            )
        
        # Prompt for API key if interactive
        if interactive:
            api_key = self._ui.prompt_for_api_key(resolved_provider, config)
            
            if not api_key:
                return StorageResult(
                    success=False,
                    message="API key setup cancelled by user"
                )
        else:
            return StorageResult(
                success=False,
                message="Non-interactive mode requires pre-provided API key",
                error_details="Use interactive mode or provide API key through other means"
            )
        
        # Validate format
        validation_result = self._validator.validate_format(resolved_provider, api_key)
        
        if not validation_result.valid:
            if interactive:
                # Ask user if they want to continue anyway
                continue_anyway = self._ui.show_validation_error(validation_result, resolved_provider)
                if not continue_anyway:
                    return StorageResult(
                        success=False,
                        message="API key setup cancelled due to validation failure",
                        error_details=validation_result.reason
                    )
            else:
                return StorageResult(
                    success=False,
                    message=f"Invalid API key format for {config.display_name}",
                    error_details=validation_result.reason
                )
        else:
            if interactive:
                log_info(f"API key validation passed for {config.display_name}")
        
        # Store the key
        storage_result = self._storage.set_api_key(resolved_provider, api_key)
        
        if storage_result.success and interactive:
            keyring_info = self._keyring.get_keyring_info()
            details = f"Stored in: {keyring_info.backend_name} keyring"
            self._ui.show_success_message(config.display_name, "API key setup", details)
        
        return storage_result
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            API key or None if not found
        """
        return self._storage.get_api_key(provider)
    
    def remove_api_key(self, provider: str) -> StorageResult:
        """
        Remove API key for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            StorageResult with operation outcome
        """
        return self._storage.remove_api_key(provider)
    
    def list_api_keys(self) -> List[ApiKeyInfo]:
        """
        List all stored API keys with metadata.
        
        Returns:
            List of ApiKeyInfo objects
        """
        return self._storage.list_stored_keys()
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information including keyring backend.
        
        Returns:
            Dictionary with system information
        """
        keyring_info = self._keyring.get_keyring_info()
        providers = self._provider_registry.get_all_providers()
        
        return {
            "keyring_info": {
                "available": keyring_info.available,
                "backend_name": keyring_info.backend_name,
                "service_name": keyring_info.service_name,
                "reason": keyring_info.reason,
                "recommendation": keyring_info.recommendation
            },
            "supported_providers": [p.name for p in providers],
            "total_providers": len(providers),
            "storage_stats": self._storage.get_storage_stats()
        }
    
    def validate_api_key(self, provider: str, api_key: str) -> ValidationResult:
        """
        Validate API key format for a provider.
        
        Args:
            provider: Provider name
            api_key: API key to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        return self._validator.validate_format(provider, api_key)
    
    def check_provider_support(self, provider: str) -> Dict[str, Any]:
        """
        Check if a provider is supported and get its configuration.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with provider support information
        """
        resolved_provider = self._provider_registry.resolve_provider_alias(provider)
        config = self._provider_registry.get_provider_config(resolved_provider)
        
        if config:
            return {
                "supported": True,
                "name": config.name,
                "display_name": config.display_name,
                "has_validation": config.api_key_pattern is not None,
                "setup_url": config.setup_url,
                "aliases": config.aliases or [],
                "has_stored_key": self._storage.has_api_key(resolved_provider)
            }
        else:
            return {
                "supported": False,
                "name": provider,
                "reason": "Provider not found in registry",
                "available_providers": [p.name for p in self._provider_registry.get_all_providers()]
            }
    
    def bulk_validate_stored_keys(self) -> Dict[str, ValidationResult]:
        """
        Validate all stored API keys.
        
        Returns:
            Dictionary mapping provider names to validation results
        """
        results = {}
        stored_keys = self._storage.list_stored_keys()
        
        for key_info in stored_keys:
            try:
                api_key = self._storage.get_api_key(key_info.provider)
                if api_key:
                    results[key_info.provider] = self._validator.validate_format(key_info.provider, api_key)
                else:
                    results[key_info.provider] = ValidationResult(
                        valid=False,
                        reason="Could not retrieve stored API key"
                    )
            except Exception as e:
                log_error(f"Failed to validate stored key for {key_info.provider}: {e}")
                results[key_info.provider] = ValidationResult(
                    valid=False,
                    reason=f"Validation error: {e}"
                )
        
        return results
    
    def export_key_metadata(self) -> Dict[str, Any]:
        """
        Export metadata about stored keys (without actual keys).
        
        Returns:
            Dictionary with key metadata for backup/migration
        """
        stored_keys = self._storage.list_stored_keys()
        
        return {
            "export_date": str(Path(__file__).stat().st_mtime),
            "keyring_backend": self._keyring.get_keyring_info().backend_name,
            "total_keys": len(stored_keys),
            "providers": [
                {
                    "name": key.provider,
                    "masked_key": key.masked_key,
                    "stored_date": key.stored_date.isoformat() if key.stored_date else None,
                    "is_valid_format": key.is_valid_format,
                    "validation_message": key.validation_message
                }
                for key in stored_keys
            ]
        }


def create_api_key_orchestrator(
    keyring_backend: IKeyringBackend,
    provider_registry: IProviderRegistry,
    validator: IApiKeyValidator,
    storage: IApiKeyStorage,
    user_interface: IUserInterface
) -> IApiKeyOrchestrator:
    """
    Factory function to create API key orchestrator.
    
    Args:
        keyring_backend: Keyring backend for secure storage
        provider_registry: Provider registry for configurations
        validator: API key validator for format checking
        storage: API key storage operations
        user_interface: User interface for interactions
        
    Returns:
        ApiKeyOrchestrator instance
    """
    return ApiKeyOrchestrator(
        keyring_backend,
        provider_registry,
        validator,
        storage,
        user_interface
    )


def create_production_orchestrator(verbose: bool = True) -> IApiKeyOrchestrator:
    """
    Factory function to create production API key orchestrator with all components.
    
    Args:
        verbose: Whether to use verbose user interface
        
    Returns:
        Fully configured ApiKeyOrchestrator instance
    """
    # Import factory functions
    from .storage.keyring_backend import create_keyring_backend
    from .providers.provider_registry import create_provider_registry
    from .validation.api_key_validator import create_api_key_validator
    from .storage.api_key_storage import create_api_key_storage
    from .ui.user_interface import create_cli_user_interface
    
    # Create components
    keyring_backend = create_keyring_backend()
    provider_registry = create_provider_registry()
    validator = create_api_key_validator(provider_registry)
    storage = create_api_key_storage(keyring_backend, provider_registry, validator)
    user_interface = create_cli_user_interface(verbose)
    
    return create_api_key_orchestrator(
        keyring_backend,
        provider_registry,
        validator,
        storage,
        user_interface
    )


def create_mock_orchestrator() -> IApiKeyOrchestrator:
    """
    Factory function to create mock API key orchestrator for testing.
    
    Returns:
        Mock ApiKeyOrchestrator instance
    """
    # Import mock factory functions
    from .storage.keyring_backend import create_mock_keyring_backend
    from .providers.provider_registry import create_mock_provider_registry
    from .validation.api_key_validator import create_mock_api_key_validator
    from .storage.api_key_storage import create_memory_api_key_storage
    from .ui.user_interface import create_mock_user_interface
    
    # Create mock components
    keyring_backend = create_mock_keyring_backend()
    provider_registry = create_mock_provider_registry()
    validator = create_mock_api_key_validator(provider_registry)
    storage = create_memory_api_key_storage(provider_registry, validator)
    user_interface = create_mock_user_interface()
    
    return create_api_key_orchestrator(
        keyring_backend,
        provider_registry,
        validator,
        storage,
        user_interface
    )

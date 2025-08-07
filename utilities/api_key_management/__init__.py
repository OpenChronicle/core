"""
API Key Management Package

This package provides secure, modular API key management for OpenChronicle
following SOLID principles with comprehensive testing support.

Main Components:
- Secure keyring-based storage with OS integration
- Provider registry with model registry integration
- API key format validation with detailed feedback
- CLI and interactive user interfaces
- Comprehensive orchestration with dependency injection

Usage:
    from utilities.api_key_management import create_api_key_manager, create_mock_api_key_manager
    
    # Production usage
    manager = create_api_key_manager()
    manager.setup_api_key("openai")
    
    # Testing usage
    mock_manager = create_mock_api_key_manager()
"""

# Main interfaces
from .interfaces.api_key_interfaces import (
    IApiKeyOrchestrator,
    IKeyringBackend,
    IProviderRegistry,
    IApiKeyValidator,
    IApiKeyStorage,
    IUserInterface,
    # Data classes
    ApiKeyInfo,
    ValidationResult,
    ProviderConfig,
    KeyringInfo,
    StorageResult,
    # Mock implementations
    MockKeyringBackend,
    MockProviderRegistry,
    MockApiKeyValidator,
    MockUserInterface
)

# Main orchestrator
from .orchestrator import (
    ApiKeyOrchestrator,
    create_api_key_orchestrator,
    create_production_orchestrator,
    create_mock_orchestrator
)

# Component factories
from .storage.keyring_backend import (
    KeyringBackend,
    FallbackKeyringBackend,
    create_keyring_backend,
    create_mock_keyring_backend
)

from .providers.provider_registry import (
    ProviderRegistry,
    StaticProviderRegistry,
    create_provider_registry,
    create_static_provider_registry,
    create_mock_provider_registry
)

from .validation.api_key_validator import (
    ApiKeyValidator,
    LenientApiKeyValidator,
    create_api_key_validator,
    create_mock_api_key_validator
)

from .storage.api_key_storage import (
    ApiKeyStorage,
    MemoryApiKeyStorage,
    create_api_key_storage,
    create_memory_api_key_storage
)

from .ui.user_interface import (
    CliUserInterface,
    SilentUserInterface,
    InteractiveManager,
    create_cli_user_interface,
    create_silent_user_interface,
    create_mock_user_interface
)

# Version info
__version__ = "2.0.0"
__author__ = "OpenChronicle Development Team"

# Main factory functions for easy usage
def create_api_key_manager(verbose: bool = True) -> IApiKeyOrchestrator:
    """
    Create production API key manager with all components.
    
    Args:
        verbose: Whether to use verbose user interface
        
    Returns:
        Fully configured API key orchestrator
    """
    return create_production_orchestrator(verbose)


def create_silent_api_key_manager() -> IApiKeyOrchestrator:
    """
    Create production API key manager with silent interface.
    
    Returns:
        API key orchestrator with silent user interface
    """
    # Import factory functions
    from .storage.keyring_backend import create_keyring_backend
    from .providers.provider_registry import create_provider_registry
    from .validation.api_key_validator import create_api_key_validator
    from .storage.api_key_storage import create_api_key_storage
    from .ui.user_interface import create_silent_user_interface
    
    # Create components
    keyring_backend = create_keyring_backend()
    provider_registry = create_provider_registry()
    validator = create_api_key_validator(provider_registry)
    storage = create_api_key_storage(keyring_backend, provider_registry, validator)
    user_interface = create_silent_user_interface()
    
    return create_api_key_orchestrator(
        keyring_backend,
        provider_registry,
        validator,
        storage,
        user_interface
    )


def create_memory_api_key_manager(verbose: bool = True) -> IApiKeyOrchestrator:
    """
    Create API key manager with memory storage (for testing/temporary use).
    
    Args:
        verbose: Whether to use verbose user interface
        
    Returns:
        API key orchestrator with memory storage
    """
    # Import factory functions
    from .storage.keyring_backend import create_mock_keyring_backend
    from .providers.provider_registry import create_provider_registry
    from .validation.api_key_validator import create_api_key_validator
    from .storage.api_key_storage import create_memory_api_key_storage
    from .ui.user_interface import create_cli_user_interface
    
    # Create components
    keyring_backend = create_mock_keyring_backend(available=False)
    provider_registry = create_provider_registry()
    validator = create_api_key_validator(provider_registry)
    storage = create_memory_api_key_storage(provider_registry, validator)
    user_interface = create_cli_user_interface(verbose)
    
    return create_api_key_orchestrator(
        keyring_backend,
        provider_registry,
        validator,
        storage,
        user_interface
    )


def create_mock_api_key_manager() -> IApiKeyOrchestrator:
    """
    Create mock API key manager for testing.
    
    Returns:
        Mock API key orchestrator with all mock components
    """
    return create_mock_orchestrator()


def create_interactive_manager(orchestrator: IApiKeyOrchestrator) -> InteractiveManager:
    """
    Create interactive manager for API key operations.
    
    Args:
        orchestrator: API key orchestrator for operations
        
    Returns:
        InteractiveManager instance
    """
    from .ui.user_interface import create_cli_user_interface
    ui = create_cli_user_interface()
    return InteractiveManager(ui)


# Export main items for easy import
__all__ = [
    # Main factory functions
    "create_api_key_manager",
    "create_silent_api_key_manager", 
    "create_memory_api_key_manager",
    "create_mock_api_key_manager",
    "create_interactive_manager",
    
    # Main interfaces
    "IApiKeyOrchestrator",
    "IKeyringBackend",
    "IProviderRegistry", 
    "IApiKeyValidator",
    "IApiKeyStorage",
    "IUserInterface",
    
    # Data classes
    "ApiKeyInfo",
    "ValidationResult",
    "ProviderConfig",
    "KeyringInfo",
    "StorageResult",
    
    # Main implementations
    "ApiKeyOrchestrator",
    "KeyringBackend",
    "ProviderRegistry",
    "ApiKeyValidator",
    "ApiKeyStorage",
    "CliUserInterface",
    "InteractiveManager",
    
    # Mock implementations
    "MockKeyringBackend",
    "MockProviderRegistry",
    "MockApiKeyValidator",
    "MockUserInterface",
    
    # Advanced factory functions
    "create_api_key_orchestrator",
    "create_production_orchestrator",
    "create_mock_orchestrator",
    "create_keyring_backend",
    "create_provider_registry",
    "create_api_key_validator",
    "create_api_key_storage",
    "create_cli_user_interface"
]

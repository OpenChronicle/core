"""
API key validator implementation for format validation.

This module provides API key format validation using provider-specific
patterns and regular expressions with detailed feedback.
"""

import re
from typing import Dict, Any
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

from ..interfaces.api_key_interfaces import IApiKeyValidator, IProviderRegistry, ValidationResult


class ApiKeyValidator(IApiKeyValidator):
    """Production API key validator with pattern matching."""
    
    def __init__(self, provider_registry: IProviderRegistry):
        """
        Initialize API key validator.
        
        Args:
            provider_registry: Provider registry for validation patterns
        """
        self._provider_registry = provider_registry
    
    def validate_format(self, provider: str, api_key: str) -> ValidationResult:
        """
        Validate API key format against provider patterns.
        
        Args:
            provider: Provider name
            api_key: API key to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        if not api_key or not api_key.strip():
            return ValidationResult(
                valid=False,
                reason="API key is empty",
                suggestion="Please provide a valid API key"
            )
        
        api_key = api_key.strip()
        
        # Get provider configuration
        config = self._provider_registry.get_provider_config(provider)
        
        if not config:
            # Unknown provider - basic validation only
            return self._basic_validation(provider, api_key)
        
        if not config.api_key_pattern:
            # No pattern available for this provider
            return ValidationResult(
                valid=len(api_key) >= 10,
                reason=f"No format pattern available for {config.display_name} - basic length check only" if len(api_key) >= 10 else "API key too short",
                suggestion="Check provider documentation for correct format",
                setup_url=config.setup_url
            )
        
        # Validate against pattern
        try:
            matches = re.match(config.api_key_pattern, api_key)
            
            if matches:
                return ValidationResult(
                    valid=True,
                    reason=f"Valid {config.display_name} API key format",
                    pattern=config.api_key_pattern
                )
            else:
                return ValidationResult(
                    valid=False,
                    reason=f"Invalid {config.display_name} API key format",
                    expected_pattern=config.api_key_pattern,
                    setup_url=config.setup_url,
                    suggestion=f"Expected format matching: {config.api_key_pattern}"
                )
                
        except re.error as e:
            log_error(f"Invalid regex pattern for {provider}: {e}")
            return ValidationResult(
                valid=len(api_key) >= 10,
                reason=f"Pattern validation failed - using basic check: {e}",
                suggestion="Check provider documentation for correct format",
                setup_url=config.setup_url if config else None
            )
    
    def _basic_validation(self, provider: str, api_key: str) -> ValidationResult:
        """
        Perform basic validation when no pattern is available.
        
        Args:
            provider: Provider name
            api_key: API key to validate
            
        Returns:
            ValidationResult with basic validation outcome
        """
        # Basic length and character checks
        if len(api_key) < 10:
            return ValidationResult(
                valid=False,
                reason="API key too short (minimum 10 characters)",
                suggestion="Check provider documentation for correct format"
            )
        
        if len(api_key) > 200:
            return ValidationResult(
                valid=False,
                reason="API key too long (maximum 200 characters)",
                suggestion="Check for extra spaces or characters"
            )
        
        # Check for obvious issues
        if api_key.count(' ') > 2:
            return ValidationResult(
                valid=False,
                reason="API key contains too many spaces",
                suggestion="Remove extra spaces and try again"
            )
        
        if any(char in api_key for char in ['<', '>', '"', "'"]):
            return ValidationResult(
                valid=False,
                reason="API key contains invalid characters",
                suggestion="Remove quotes or brackets and try again"
            )
        
        return ValidationResult(
            valid=True,
            reason=f"Basic validation passed for {provider} (no format pattern available)",
            suggestion="Verify with provider if this key format is correct"
        )
    
    def get_validation_info(self, provider: str) -> Dict[str, Any]:
        """
        Get validation information for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with validation information
        """
        config = self._provider_registry.get_provider_config(provider)
        
        if not config:
            return {
                "provider": provider,
                "supported": False,
                "reason": "Provider not found in registry"
            }
        
        return {
            "provider": config.name,
            "display_name": config.display_name,
            "supported": True,
            "has_pattern": config.api_key_pattern is not None,
            "pattern": config.api_key_pattern,
            "setup_url": config.setup_url,
            "description": config.description,
            "aliases": config.aliases or []
        }
    
    def validate_multiple_keys(self, keys: Dict[str, str]) -> Dict[str, ValidationResult]:
        """
        Validate multiple API keys at once.
        
        Args:
            keys: Dictionary of provider -> api_key mappings
            
        Returns:
            Dictionary of provider -> ValidationResult mappings
        """
        results = {}
        
        for provider, api_key in keys.items():
            try:
                results[provider] = self.validate_format(provider, api_key)
            except Exception as e:
                log_error(f"Failed to validate key for {provider}: {e}")
                results[provider] = ValidationResult(
                    valid=False,
                    reason=f"Validation error: {e}",
                    suggestion="Check API key format and try again"
                )
        
        return results
    
    def get_provider_examples(self, provider: str) -> Dict[str, Any]:
        """
        Get example API key formats for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with example information
        """
        config = self._provider_registry.get_provider_config(provider)
        
        if not config:
            return {"provider": provider, "examples": []}
        
        # Generate example based on pattern
        examples = []
        if config.api_key_pattern:
            if "sk-" in config.api_key_pattern:
                examples.append("sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            elif "sk-ant-" in config.api_key_pattern:
                examples.append("sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            elif "AI" in config.api_key_pattern:
                examples.append("AIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            elif "gsk_" in config.api_key_pattern:
                examples.append("gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            elif "hf_" in config.api_key_pattern:
                examples.append("hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        
        return {
            "provider": config.name,
            "display_name": config.display_name,
            "examples": examples,
            "setup_url": config.setup_url,
            "description": config.description
        }


class LenientApiKeyValidator(IApiKeyValidator):
    """Lenient validator that accepts most reasonable-looking API keys."""
    
    def __init__(self, provider_registry: IProviderRegistry):
        """
        Initialize lenient validator.
        
        Args:
            provider_registry: Provider registry (used for metadata only)
        """
        self._provider_registry = provider_registry
    
    def validate_format(self, provider: str, api_key: str) -> ValidationResult:
        """
        Perform lenient validation (mainly length and basic checks).
        
        Args:
            provider: Provider name
            api_key: API key to validate
            
        Returns:
            ValidationResult with lenient validation outcome
        """
        if not api_key or not api_key.strip():
            return ValidationResult(
                valid=False,
                reason="API key is empty",
                suggestion="Please provide a valid API key"
            )
        
        api_key = api_key.strip()
        
        # Very basic validation
        if len(api_key) < 5:
            return ValidationResult(
                valid=False,
                reason="API key too short",
                suggestion="API key should be at least 5 characters"
            )
        
        if len(api_key) > 500:
            return ValidationResult(
                valid=False,
                reason="API key too long",
                suggestion="API key should be less than 500 characters"
            )
        
        return ValidationResult(
            valid=True,
            reason=f"Lenient validation passed for {provider}",
            suggestion="Key format accepted - verify with provider if needed"
        )
    
    def get_validation_info(self, provider: str) -> Dict[str, Any]:
        """Get validation information (lenient mode)."""
        config = self._provider_registry.get_provider_config(provider)
        
        return {
            "provider": provider,
            "display_name": config.display_name if config else provider.title(),
            "validation_mode": "lenient",
            "supported": True,
            "has_pattern": False,
            "setup_url": config.setup_url if config else None
        }


def create_api_key_validator(provider_registry: IProviderRegistry, lenient: bool = False) -> IApiKeyValidator:
    """
    Factory function to create API key validator.
    
    Args:
        provider_registry: Provider registry for validation patterns
        lenient: Whether to use lenient validation
        
    Returns:
        ApiKeyValidator or LenientApiKeyValidator instance
    """
    if lenient:
        return LenientApiKeyValidator(provider_registry)
    else:
        return ApiKeyValidator(provider_registry)


def create_mock_api_key_validator(provider_registry: IProviderRegistry) -> IApiKeyValidator:
    """
    Factory function to create mock API key validator for testing.
    
    Args:
        provider_registry: Provider registry for mock validator
        
    Returns:
        MockApiKeyValidator instance
    """
    from ..interfaces.api_key_interfaces import MockApiKeyValidator
    return MockApiKeyValidator(provider_registry)

"""
User interface implementation for API key management.

This module provides CLI and interactive interfaces for API key management
with secure prompts and user-friendly feedback.
"""

import getpass
import sys
from typing import Optional
from pathlib import Path

# Add utilities to path for logging
sys.path.append(str(Path(__file__).parent.parent.parent))
try:
    from logging_system import log_info as _log_info, log_error as _log_error
    def log_info(msg): _log_info(msg)
    def log_error(msg): _log_error(msg)
except ImportError:
    # Fallback logging if logging_system not available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    def log_info(msg): logger.info(msg)
    def log_error(msg): logger.error(msg)

from ..interfaces.api_key_interfaces import IUserInterface, ValidationResult, ProviderConfig


class CliUserInterface(IUserInterface):
    """Command-line interface for user interactions."""
    
    def __init__(self, verbose: bool = True):
        """
        Initialize CLI interface.
        
        Args:
            verbose: Whether to show detailed messages
        """
        self._verbose = verbose
    
    def prompt_for_api_key(self, provider: str, config: ProviderConfig) -> Optional[str]:
        """
        Securely prompt user for API key.
        
        Args:
            provider: Provider name
            config: Provider configuration
            
        Returns:
            API key or None if cancelled
        """
        if self._verbose:
            print(f"\n🔐 Secure API Key Setup for {config.display_name}")
            print("=" * 50)
            
            if config.setup_url:
                print(f"Get your API key at: {config.setup_url}")
            
            if config.description:
                print(f"Description: {config.description}")
            
            if config.api_key_pattern:
                # Show example format
                example = self._generate_example(config.api_key_pattern)
                if example:
                    print(f"Expected format: {example}")
            
            print()
        
        try:
            api_key = getpass.getpass(f"Enter {config.display_name} API key (input hidden): ").strip()
            
            if not api_key:
                if self._verbose:
                    print("❌ No API key provided.")
                return None
            
            return api_key
            
        except KeyboardInterrupt:
            if self._verbose:
                print("\n❌ Cancelled by user")
            return None
        except Exception as e:
            if self._verbose:
                print(f"❌ Error: {e}")
            log_error(f"Failed to prompt for API key: {e}")
            return None
    
    def show_validation_error(self, result: ValidationResult, provider: str) -> bool:
        """
        Show validation error and ask if user wants to continue.
        
        Args:
            result: Validation result
            provider: Provider name
            
        Returns:
            True if user wants to continue, False otherwise
        """
        if self._verbose:
            print(f"❌ {result.reason}")
            
            if result.expected_pattern:
                print(f"   Expected pattern: {result.expected_pattern}")
            
            if result.setup_url:
                print(f"   Get correct API key at: {result.setup_url}")
            
            if result.suggestion:
                print(f"   {result.suggestion}")
        
        try:
            continue_anyway = input("\nStore anyway? This may cause connection failures (y/N): ").strip().lower()
            return continue_anyway in ['y', 'yes']
        except KeyboardInterrupt:
            if self._verbose:
                print("\n❌ Cancelled by user")
            return False
        except Exception:
            return False
    
    def show_success_message(self, provider: str, operation: str, details: str = "") -> None:
        """Show success message to user."""
        if self._verbose:
            message = f"✅ {operation} successful"
            if provider:
                message += f" for {provider}"
            if details:
                message += f": {details}"
            print(message)
    
    def show_error_message(self, message: str, details: str = "") -> None:
        """Show error message to user."""
        if self._verbose:
            error_msg = f"❌ {message}"
            if details:
                error_msg += f": {details}"
            print(error_msg)
    
    def confirm_action(self, message: str, default: bool = False) -> bool:
        """
        Ask user to confirm an action.
        
        Args:
            message: Confirmation message
            default: Default response if user just presses enter
            
        Returns:
            True if confirmed, False otherwise
        """
        if not self._verbose:
            return default
        
        default_text = "(Y/n)" if default else "(y/N)"
        
        try:
            response = input(f"{message} {default_text}: ").strip().lower()
            
            if not response:
                return default
            
            return response in ['y', 'yes']
            
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            return False
        except Exception:
            return default
    
    def _generate_example(self, pattern: str) -> Optional[str]:
        """
        Generate example API key format from regex pattern.
        
        Args:
            pattern: Regex pattern
            
        Returns:
            Example string or None
        """
        # Simple pattern-to-example mapping
        if "sk-" in pattern and "48" in pattern:
            return "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        elif "sk-ant-" in pattern and "95" in pattern:
            return "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        elif "AI" in pattern and "35" in pattern:
            return "AIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        elif "gsk_" in pattern and "52" in pattern:
            return "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        elif "hf_" in pattern and "37" in pattern:
            return "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        
        return None


class SilentUserInterface(IUserInterface):
    """Silent interface for non-interactive operations."""
    
    def __init__(self):
        """Initialize silent interface."""
        pass
    
    def prompt_for_api_key(self, provider: str, config: ProviderConfig) -> Optional[str]:
        """Silent interface cannot prompt for input."""
        return None
    
    def show_validation_error(self, result: ValidationResult, provider: str) -> bool:
        """Silent interface always returns False for validation errors."""
        return False
    
    def show_success_message(self, provider: str, operation: str, details: str = "") -> None:
        """Silent interface does not show messages."""
        pass
    
    def show_error_message(self, message: str, details: str = "") -> None:
        """Silent interface does not show messages."""
        pass
    
    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Silent interface returns default value."""
        return default


class InteractiveManager:
    """Interactive mode manager for API key operations."""
    
    def __init__(self, ui: IUserInterface):
        """
        Initialize interactive manager.
        
        Args:
            ui: User interface implementation
        """
        self._ui = ui
    
    def run_interactive_mode(self, orchestrator) -> None:
        """
        Run interactive API key management mode.
        
        Args:
            orchestrator: API key orchestrator for operations
        """
        print("🔐 OpenChronicle API Key Manager - Interactive Mode")
        print("=" * 50)
        
        while True:
            print("\nCommands:")
            print("  1. Set API key")
            print("  2. List stored keys")
            print("  3. Remove API key")
            print("  4. Show system info")
            print("  5. Validate API key")
            print("  6. Exit")
            
            try:
                choice = input("\nSelect option (1-6): ").strip()
                
                if choice == '1':
                    self._handle_set_key(orchestrator)
                elif choice == '2':
                    self._handle_list_keys(orchestrator)
                elif choice == '3':
                    self._handle_remove_key(orchestrator)
                elif choice == '4':
                    self._handle_system_info(orchestrator)
                elif choice == '5':
                    self._handle_validate_key(orchestrator)
                elif choice == '6':
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please select 1-6.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                self._ui.show_error_message("Interactive mode error", str(e))
    
    def _handle_set_key(self, orchestrator) -> None:
        """Handle setting an API key."""
        provider = input("Enter provider name: ").strip().lower()
        if provider:
            result = orchestrator.setup_api_key(provider, interactive=True)
            if result.success:
                self._ui.show_success_message(provider, "API key setup", result.message)
            else:
                self._ui.show_error_message(result.message, result.error_details or "")
        else:
            self._ui.show_error_message("Invalid provider name")
    
    def _handle_list_keys(self, orchestrator) -> None:
        """Handle listing stored keys."""
        keys = orchestrator.list_api_keys()
        
        if keys:
            print("\n🔑 Stored API keys:")
            for key_info in sorted(keys, key=lambda k: k.provider):
                status = "✅" if key_info.is_valid_format else "⚠️"
                print(f"  {status} {key_info.provider}: {key_info.masked_key}")
                if not key_info.is_valid_format and key_info.validation_message:
                    print(f"      Warning: {key_info.validation_message}")
            
            print(f"\nTotal: {len(keys)} API keys stored")
        else:
            print("\n📭 No API keys stored")
            print("Use option 1 to store API keys securely.")
    
    def _handle_remove_key(self, orchestrator) -> None:
        """Handle removing an API key."""
        provider = input("Enter provider to remove: ").strip().lower()
        if provider:
            if self._ui.confirm_action(f"Remove API key for {provider}?", False):
                result = orchestrator.remove_api_key(provider)
                if result.success:
                    self._ui.show_success_message(provider, "API key removal", result.message)
                else:
                    self._ui.show_error_message(result.message, result.error_details or "")
        else:
            self._ui.show_error_message("Invalid provider name")
    
    def _handle_system_info(self, orchestrator) -> None:
        """Handle showing system information."""
        info = orchestrator.get_system_info()
        
        print("\n🔐 System Information:")
        keyring_info = info.get("keyring_info", {})
        print(f"  Keyring Available: {keyring_info.get('available', False)}")
        print(f"  Backend: {keyring_info.get('backend_name', 'Unknown')}")
        print(f"  Service: {keyring_info.get('service_name', 'Unknown')}")
        
        if not keyring_info.get('available', False):
            reason = keyring_info.get('reason', 'Unknown')
            recommendation = keyring_info.get('recommendation', 'Check installation')
            print(f"  Issue: {reason}")
            print(f"  Recommendation: {recommendation}")
        
        providers = info.get("supported_providers", [])
        if providers:
            print(f"\n📋 Supported providers ({len(providers)}):")
            for provider in sorted(providers):
                print(f"    • {provider}")
    
    def _handle_validate_key(self, orchestrator) -> None:
        """Handle validating an API key."""
        provider = input("Enter provider name: ").strip().lower()
        if not provider:
            self._ui.show_error_message("Invalid provider name")
            return
        
        api_key = getpass.getpass(f"Enter {provider} API key to validate (input hidden): ").strip()
        if not api_key:
            self._ui.show_error_message("No API key provided")
            return
        
        result = orchestrator.validate_api_key(provider, api_key)
        
        if result.valid:
            print(f"✅ {result.reason}")
        else:
            print(f"❌ {result.reason}")
            if result.suggestion:
                print(f"   Suggestion: {result.suggestion}")
            if result.setup_url:
                print(f"   Get API key at: {result.setup_url}")


def create_cli_user_interface(verbose: bool = True) -> IUserInterface:
    """
    Factory function to create CLI user interface.
    
    Args:
        verbose: Whether to show detailed messages
        
    Returns:
        CliUserInterface instance
    """
    return CliUserInterface(verbose)


def create_silent_user_interface() -> IUserInterface:
    """
    Factory function to create silent user interface.
    
    Returns:
        SilentUserInterface instance
    """
    return SilentUserInterface()


def create_mock_user_interface() -> IUserInterface:
    """
    Factory function to create mock user interface for testing.
    
    Returns:
        MockUserInterface instance
    """
    from ..interfaces.api_key_interfaces import MockUserInterface
    return MockUserInterface()

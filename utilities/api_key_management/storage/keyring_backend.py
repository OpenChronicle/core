"""
Keyring backend implementation for secure API key storage.

This module provides OS-level secure storage using the keyring library
with graceful fallback when keyring is not available.
"""

from typing import Optional
import sys
from pathlib import Path

# Add utilities to path for logging
sys.path.append(str(Path(__file__).parent.parent.parent))
try:
    from logging_system import log_info as _log_info, log_error as _log_error, log_system_event as _log_system_event
    def log_info(msg): _log_info(msg)
    def log_error(msg): _log_error(msg)
    def log_system_event(event, msg): _log_system_event(event, msg)
except ImportError:
    # Fallback logging if logging_system not available
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    def log_info(msg): logger.info(msg)
    def log_error(msg): logger.error(msg)
    def log_system_event(event, msg): logger.info(f"{event}: {msg}")

from ..interfaces.api_key_interfaces import IKeyringBackend, KeyringInfo

# Optional keyring import with graceful fallback
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    keyring = None

# Service name for keyring storage
KEYRING_SERVICE = "openchronicle"


class KeyringBackend(IKeyringBackend):
    """Production keyring backend using OS keyring for secure storage."""
    
    def __init__(self, service_name: str = KEYRING_SERVICE):
        """
        Initialize keyring backend.
        
        Args:
            service_name: Service name for keyring storage
        """
        self._service_name = service_name
        self._available = KEYRING_AVAILABLE and keyring is not None
    
    def is_available(self) -> bool:
        """Check if keyring is available for secure storage."""
        return self._available
    
    def get_keyring_info(self) -> KeyringInfo:
        """Get information about the keyring backend."""
        if not self._available:
            return KeyringInfo(
                available=False,
                backend_name=None,
                service_name=self._service_name,
                reason="keyring library not installed" if not KEYRING_AVAILABLE else "keyring not functional",
                recommendation="Install with: pip install keyring"
            )
        
        try:
            backend = keyring.get_keyring()
            backend_name = backend.__class__.__name__ if backend else "Unknown"
            
            return KeyringInfo(
                available=True,
                backend_name=backend_name,
                service_name=self._service_name,
                reason=None,
                recommendation=None
            )
        except Exception as e:
            log_error(f"Failed to get keyring info: {e}")
            return KeyringInfo(
                available=False,
                backend_name=None,
                service_name=self._service_name,
                reason=f"keyring error: {e}",
                recommendation="Check keyring installation and OS support"
            )
    
    def get_password(self, service: str, username: str) -> Optional[str]:
        """
        Retrieve password from keyring.
        
        Args:
            service: Service name
            username: Username/identifier
            
        Returns:
            Password or None if not found/not available
        """
        if not self._available:
            return None
        
        try:
            password = keyring.get_password(service, username)
            if password:
                log_info(f"Retrieved password for {username} from secure storage")
            return password
        except Exception as e:
            log_error(f"Failed to retrieve password for {username}: {e}")
            return None
    
    def set_password(self, service: str, username: str, password: str) -> bool:
        """
        Store password in keyring.
        
        Args:
            service: Service name
            username: Username/identifier
            password: Password to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self._available:
            log_error("Keyring not available for secure storage")
            return False
        
        try:
            keyring.set_password(service, username, password)
            log_system_event("password_stored", f"Password stored securely for {username}")
            log_info(f"Password stored securely for {username}")
            return True
        except Exception as e:
            log_error(f"Failed to store password for {username}: {e}")
            return False
    
    def delete_password(self, service: str, username: str) -> bool:
        """
        Delete password from keyring.
        
        Args:
            service: Service name
            username: Username/identifier
            
        Returns:
            True if successful, False if not found/error
        """
        if not self._available:
            log_error("Keyring not available")
            return False
        
        try:
            # Check if password exists first
            existing_password = keyring.get_password(service, username)
            if not existing_password:
                log_info(f"No password found for {username}")
                return False
            
            keyring.delete_password(service, username)
            log_system_event("password_removed", f"Password removed for {username}")
            log_info(f"Password removed for {username}")
            return True
        except Exception as e:
            log_error(f"Failed to remove password for {username}: {e}")
            return False


class FallbackKeyringBackend(IKeyringBackend):
    """
    Fallback keyring backend when OS keyring is not available.
    
    This implementation provides a consistent interface but cannot actually
    store passwords securely. It's used for testing or when keyring is unavailable.
    """
    
    def __init__(self, service_name: str = KEYRING_SERVICE):
        """
        Initialize fallback backend.
        
        Args:
            service_name: Service name (for interface compatibility)
        """
        self._service_name = service_name
    
    def is_available(self) -> bool:
        """Fallback backend is never considered available for real storage."""
        return False
    
    def get_keyring_info(self) -> KeyringInfo:
        """Get information about the fallback backend."""
        return KeyringInfo(
            available=False,
            backend_name="FallbackBackend",
            service_name=self._service_name,
            reason="OS keyring not available - using fallback",
            recommendation="Install keyring library for secure storage: pip install keyring"
        )
    
    def get_password(self, service: str, username: str) -> Optional[str]:
        """Fallback cannot retrieve passwords."""
        return None
    
    def set_password(self, service: str, username: str, password: str) -> bool:
        """Fallback cannot store passwords securely."""
        log_error("Cannot store password securely - keyring not available")
        return False
    
    def delete_password(self, service: str, username: str) -> bool:
        """Fallback cannot delete passwords."""
        return False


def create_keyring_backend(service_name: str = KEYRING_SERVICE) -> IKeyringBackend:
    """
    Factory function to create appropriate keyring backend.
    
    Args:
        service_name: Service name for keyring storage
        
    Returns:
        KeyringBackend if available, FallbackKeyringBackend otherwise
    """
    if KEYRING_AVAILABLE and keyring is not None:
        return KeyringBackend(service_name)
    else:
        return FallbackKeyringBackend(service_name)


def create_mock_keyring_backend(available: bool = True) -> IKeyringBackend:
    """
    Factory function to create mock keyring backend for testing.
    
    Args:
        available: Whether mock backend should be available
        
    Returns:
        MockKeyringBackend instance
    """
    from ..interfaces.api_key_interfaces import MockKeyringBackend
    return MockKeyringBackend(available)

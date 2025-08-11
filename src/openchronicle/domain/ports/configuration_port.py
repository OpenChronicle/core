"""
Configuration port for domain layer.
Abstract interface for configuration management without infrastructure dependencies.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class IConfigurationPort(ABC):
    """Port for configuration management in domain layer."""
    
    @abstractmethod
    async def get_config(self, key: str) -> Optional[Any]:
        """Get configuration value by key."""
        pass
    
    @abstractmethod
    async def set_config(self, key: str, value: Any) -> bool:
        """Set configuration value."""
        pass
    
    @abstractmethod
    async def get_all_configs(self) -> Dict[str, Any]:
        """Get all configuration values."""
        pass


class IRegistryPort(ABC):
    """Port for model registry operations in domain layer."""
    
    @abstractmethod
    async def discover_models(self) -> List[Dict[str, Any]]:
        """Discover available models."""
        pass
    
    @abstractmethod
    async def get_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific model."""
        pass
    
    @abstractmethod
    async def register_model(self, model_config: Dict[str, Any]) -> bool:
        """Register a new model configuration."""
        pass


class IPerformancePort(ABC):
    """Port for performance monitoring in domain layer."""
    
    @abstractmethod
    async def record_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a performance metric."""
        pass
    
    @abstractmethod
    async def get_metrics(self, name: str, start_time: float = None) -> List[Dict]:
        """Get recorded metrics."""
        pass


class IStoragePort(ABC):
    """Port for storage operations in domain layer."""
    
    @abstractmethod
    async def store_data(self, key: str, data: Any) -> bool:
        """Store data with given key."""
        pass
    
    @abstractmethod
    async def retrieve_data(self, key: str) -> Optional[Any]:
        """Retrieve data by key."""
        pass

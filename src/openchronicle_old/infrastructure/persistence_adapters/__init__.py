"""
Persistence Adapters - Infrastructure implementations for data persistence

This module contains concrete implementations of the domain persistence interfaces.
These adapters provide the actual database functionality while maintaining
the dependency inversion principle.
"""

from .memory_adapter import MemoryAdapter
from .performance_adapter import PerformanceAdapter
from .persistence_adapter import PersistenceAdapter
from .registry_adapter import RegistryAdapter
from .storage_adapter import StorageAdapter

__all__ = [
    "PersistenceAdapter",
    "MemoryAdapter",
    "StorageAdapter",
    "RegistryAdapter",
    "PerformanceAdapter",
]

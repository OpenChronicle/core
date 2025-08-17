"""
Bootstrap Composition Root

Creates and wires infrastructure adapters with domain services
following dependency injection patterns for clean architecture.
"""

from typing import Optional

from openchronicle.domain.ports.memory_port import IMemoryPort
from openchronicle.domain.services.narrative.engines.consistency.consistency_orchestrator import (
    ConsistencyOrchestrator,
)
from openchronicle.infrastructure.adapters.memory_port_adapter import MemoryPortAdapter


def create_consistency_orchestrator(config: Optional[dict] = None) -> ConsistencyOrchestrator:
    """
    Create and wire ConsistencyOrchestrator with required dependencies.

    This composition root function creates infrastructure adapters and injects
    them into domain services, maintaining clean architecture boundaries.

    Args:
        config: Optional configuration dictionary

    Returns:
        Fully configured ConsistencyOrchestrator instance
    """
    # Create infrastructure adapters
    memory_port: IMemoryPort = MemoryPortAdapter()

    # Inject dependencies into domain service
    orchestrator = ConsistencyOrchestrator(memory_port, config)

    return orchestrator


def create_memory_port_adapter() -> IMemoryPort:
    """
    Create a memory port adapter instance.

    Returns:
        Configured memory port adapter
    """
    return MemoryPortAdapter()

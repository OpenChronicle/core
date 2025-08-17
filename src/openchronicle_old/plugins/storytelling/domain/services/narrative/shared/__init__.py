"""
OpenChronicle Core - Narrative Systems Shared Components

Common utilities, base classes, and shared functionality for all narrative components.
"""

from .narrative_base import (
    EventProcessor,
    NarrativeComponent,
    NarrativeEvent,
    StateManager,
    ValidationBase,
    ValidationResult,
)
from .narrative_state import NarrativeState, NarrativeStateManager

__all__ = [
    "EventProcessor",
    "NarrativeComponent",
    "NarrativeEvent",
    "NarrativeState",
    "NarrativeStateManager",
    "StateManager",
    "ValidationBase",
    "ValidationResult",
]

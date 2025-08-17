"""
Character Core Infrastructure

Core infrastructure components that provide the foundation for all character management.
These components are used throughout the character system.

Components:
- character_base.py - Base classes and interfaces
- character_data.py - Data structures and enums
- character_storage.py - Data persistence
"""

from .character_base import (
    CharacterBehaviorProvider,
    CharacterEngineBase,
    CharacterEventHandler,
    CharacterStateProvider,
    CharacterValidationProvider,
)
from .character_data import (
    CharacterBehaviorType,
    CharacterData,
    CharacterInteractionType,
    CharacterRelationType,
    CharacterStats,
    CharacterStatType,
)
from .character_storage import CharacterStorage

__all__ = [
    "CharacterBehaviorProvider",
    "CharacterBehaviorType",
    "CharacterData",
    "CharacterEngineBase",
    "CharacterEventHandler",
    "CharacterInteractionType",
    "CharacterRelationType",
    "CharacterStatType",
    "CharacterStats",
    "CharacterStateProvider",
    "CharacterStorage",
    "CharacterValidationProvider",
]

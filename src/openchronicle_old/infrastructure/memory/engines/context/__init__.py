"""
Context Management Components

This package provides specialized components for context generation and world state
management in the OpenChronicle runtime AI engine.

Components:
- ContextBuilder: Advanced context generation for runtime AI prompts
- WorldStateManager: World state, events, and flags management
- SceneContextManager: Frame-specific context and runtime continuity

Usage:
    from .context_builder import ContextBuilder, ContextConfiguration, ContextMetrics
    from .world_state_manager import WorldStateManager, WorldStateAnalysis, EventFilter
    from .scene_context_manager import SceneContextManager, SceneContext, ContextContinuity
"""

from .context_builder import ContextBuilder, ContextConfiguration, ContextMetrics
from .scene_context_manager import ContextContinuity
from .scene_context_manager import SceneContext as FrameContext
from .scene_context_manager import SceneContextManager as FrameContextManager
from .scene_context_manager import SceneTransition as FrameTransition
from .world_state_manager import (
    EventFilter,
    WorldStateAnalysis,
    WorldStateManager,
    WorldStateUpdate,
)

__all__ = [
    "ContextBuilder",
    "ContextConfiguration",
    "ContextContinuity",
    "ContextMetrics",
    "EventFilter",
    "FrameContext",
    "FrameContextManager",
    "FrameTransition",
    "WorldStateAnalysis",
    "WorldStateManager",
    "WorldStateUpdate",
]

"""
Compatibility layer for ModelManager replacement.

This module provides a seamless transition from the old ModelManager monolith 
to the new ModelOrchestrator component-based architecture.
"""

from typing import Any
from core.model_management.model_orchestrator import ModelOrchestrator

# Create a type alias for backward compatibility
ModelManager = ModelOrchestrator

def create_model_manager() -> ModelOrchestrator:
    """
    Factory function for creating ModelManager instances.
    
    This function maintains compatibility with existing code while
    providing the new ModelOrchestrator implementation.
    
    Returns:
        ModelOrchestrator: Clean, component-based model manager
    """
    return ModelOrchestrator()

# Export the main class for import compatibility
__all__ = ['ModelManager', 'create_model_manager']

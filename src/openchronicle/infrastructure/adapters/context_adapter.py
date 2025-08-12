"""
Context Adapter - Infrastructure Implementation

Implements the context port interface using the concrete context orchestrator.
This adapter sits in the infrastructure layer and implements the domain port.
"""

from typing import Any

from openchronicle.domain.ports.context_port import IContextPort
from openchronicle.shared.logging_system import log_error
from openchronicle.shared.logging_system import log_warning

# Safe import of infrastructure component
try:
    from openchronicle.infrastructure.content.context import ContextOrchestrator
except ImportError:
    ContextOrchestrator = None


class ContextAdapter(IContextPort):
    """
    Infrastructure adapter that implements the context port interface.
    
    This adapter bridges the domain port interface with the concrete
    infrastructure implementation (ContextOrchestrator).
    """

    def __init__(self):
        """Initialize the context adapter."""
        if ContextOrchestrator is None:
            raise RuntimeError("ContextOrchestrator not available. Check infrastructure.content.context imports.")
        
        self._orchestrator = ContextOrchestrator()

    async def build_context_with_analysis(
        self, user_input: str, story_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Build context with intelligent analysis."""
        try:
            return await self._orchestrator.build_context_with_analysis(user_input, story_data)
        except (RuntimeError, AttributeError, OSError, ValueError, KeyError, TypeError) as e:
            log_warning(f"build_context_with_analysis failed: {e}")
            return await self.build_basic_context(user_input, story_data)

    async def build_basic_context(
        self, user_input: str, story_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Build basic context without analysis."""
        try:
            # Use basic method if available
            if hasattr(self._orchestrator, 'build_basic_context'):
                return await self._orchestrator.build_basic_context(user_input, story_data)
            else:
                # Fallback implementation
                return {
                    "user_input": user_input,
                    "story_data": story_data,
                    "context_type": "basic"
                }
        except (RuntimeError, AttributeError, OSError, ValueError, KeyError, TypeError) as e:
            log_error(f"build_basic_context failed: {e}")
            return {
                "user_input": user_input,
                "story_data": story_data,
                "context_type": "fallback",
                "error": str(e)
            }

    async def extract_context_metadata(
        self, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract metadata from context."""
        try:
            # Use extraction method if available
            if hasattr(self._orchestrator, 'extract_metadata'):
                return await self._orchestrator.extract_metadata(context)
            else:
                # Fallback implementation
                return {
                    "context_size": len(str(context)),
                    "has_user_input": "user_input" in context,
                    "has_story_data": "story_data" in context
                }
        except (RuntimeError, AttributeError, OSError, ValueError, KeyError, TypeError) as e:
            log_warning(f"extract_context_metadata failed: {e}")
            return {"error": str(e)}

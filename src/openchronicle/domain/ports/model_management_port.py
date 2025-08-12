"""
Model Management Port - Interface for AI model operations

Defines the contract for AI model management operations that the domain layer needs.
This interface is implemented by infrastructure adapters.
"""

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openchronicle.domain import ModelResponse
    from openchronicle.domain import NarrativeContext


class IModelManagementPort(ABC):
    """Interface for AI model management operations."""

    @abstractmethod
    async def generate_response(
        self, context: "NarrativeContext", model_preference: str | None = None
    ) -> "ModelResponse":
        """
        Generate AI response using preferred model with fallbacks.

        Args:
            context: Narrative context for response generation
            model_preference: Optional preferred model name

        Returns:
            Model response with generated content and metadata
        """

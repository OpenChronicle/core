"""
Story Processing Service Factory - Application Layer

Provides factory methods for creating properly configured StoryProcessingService
instances with correct dependency injection for different environments.
"""

from typing import Any

from openchronicle.application.services.story_processing_service import StoryProcessingConfig
from openchronicle.application.services.story_processing_service import StoryProcessingService
from openchronicle.domain.services import CharacterService
from openchronicle.domain.services import MemoryService
from openchronicle.domain.services import SceneService
from openchronicle.domain.services import StoryService


class StoryProcessingServiceFactory:
    """
    Factory for creating StoryProcessingService instances with proper dependency injection.

    This factory handles the wiring of infrastructure dependencies to application services,
    maintaining clean hexagonal architecture boundaries.
    """

    @staticmethod
    def create_production_service(
        story_service: StoryService,
        character_service: CharacterService,
        scene_service: SceneService,
        memory_service: MemoryService,
        logging_service: Any,
        cache_service: Any,
        config: StoryProcessingConfig | None = None,
    ) -> StoryProcessingService:
        """
        Create a StoryProcessingService for production use.

        Args:
            story_service: Story domain service
            character_service: Character domain service
            scene_service: Scene domain service
            memory_service: Memory domain service
            logging_service: Logging service
            cache_service: Cache service
            config: Optional configuration

        Returns:
            Configured StoryProcessingService with production adapters
        """
        from openchronicle.application.services.model_orchestrator_factory import ModelOrchestratorFactory
        from openchronicle.infrastructure.adapters.content_analysis_adapter import ContentAnalysisAdapter
        from openchronicle.infrastructure.adapters.context_adapter import ContextAdapter

        # Create production adapters
        context_port = ContextAdapter()

        # Create model orchestrator for content analysis
        model_orchestrator = ModelOrchestratorFactory.create_production_orchestrator()
        content_analysis_port = ContentAnalysisAdapter(model_orchestrator)

        return StoryProcessingService(
            story_service=story_service,
            character_service=character_service,
            scene_service=scene_service,
            memory_service=memory_service,
            logging_service=logging_service,
            cache_service=cache_service,
            config=config or StoryProcessingConfig(),
            context_port=context_port,
            content_analysis_port=content_analysis_port,
        )

    @staticmethod
    def create_test_service(
        story_service: StoryService,
        character_service: CharacterService,
        scene_service: SceneService,
        memory_service: MemoryService,
        logging_service: Any,
        cache_service: Any,
        config: StoryProcessingConfig | None = None,
    ) -> StoryProcessingService:
        """
        Create a StoryProcessingService for testing.

        Args:
            story_service: Story domain service
            character_service: Character domain service
            scene_service: Scene domain service
            memory_service: Memory domain service
            logging_service: Logging service
            cache_service: Cache service
            config: Optional configuration

        Returns:
            Configured StoryProcessingService with mock adapters
        """
        # For testing, we can use the fallback mocks built into the service
        # or inject specific test doubles as needed
        return StoryProcessingService(
            story_service=story_service,
            character_service=character_service,
            scene_service=scene_service,
            memory_service=memory_service,
            logging_service=logging_service,
            cache_service=cache_service,
            config=config or StoryProcessingConfig(),
            context_port=None,  # Will use mock fallback
            content_analysis_port=None,  # Will use mock fallback
        )

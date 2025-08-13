"""
Content Analysis Adapter - Infrastructure Implementation

Implements the content analysis port interface using the concrete content analyzer.
This adapter sits in the infrastructure layer and implements the domain port.
"""

from typing import Any

from openchronicle.domain.ports.content_analysis_port import IContentAnalysisPort
from openchronicle.shared.logging_system import log_error
from openchronicle.shared.logging_system import log_warning


# Safe import of infrastructure component
try:
    from openchronicle.infrastructure.content import ContentAnalysisOrchestrator
except ImportError:
    ContentAnalysisOrchestrator = None


class ContentAnalysisAdapter(IContentAnalysisPort):
    """
    Infrastructure adapter that implements the content analysis port interface.

    This adapter bridges the domain port interface with the concrete
    infrastructure implementation (ContentAnalysisOrchestrator).
    """

    def __init__(self, model_orchestrator):
        """
        Initialize the content analysis adapter.

        Args:
            model_orchestrator: Model orchestrator for AI operations
        """
        if ContentAnalysisOrchestrator is None:
            raise RuntimeError("ContentAnalysisOrchestrator not available. Check infrastructure.content imports.")

        self._analyzer = ContentAnalysisOrchestrator(model_orchestrator)

    async def generate_content_flags(
        self, analysis: dict[str, Any], content: str
    ) -> list[dict[str, Any]]:
        """Generate content flags based on analysis and content."""
        try:
            return await self._analyzer.generate_content_flags(analysis, content)
        except (RuntimeError, AttributeError, OSError, ValueError, KeyError, TypeError) as e:
            log_warning(f"generate_content_flags failed: {e}")
            return []

    async def analyze_content_sentiment(self, content: str) -> dict[str, Any]:
        """Analyze sentiment of content."""
        try:
            # Use underlying methods if available
            if hasattr(self._analyzer, 'analyze_sentiment'):
                return await self._analyzer.analyze_sentiment(content)
            else:
                # Fallback implementation
                return {"sentiment": "neutral", "confidence": 0.5}
        except (RuntimeError, AttributeError, OSError, ValueError, KeyError, TypeError) as e:
            log_warning(f"analyze_content_sentiment failed: {e}")
            return {"sentiment": "neutral", "confidence": 0.0}

    async def detect_content_themes(self, content: str) -> list[str]:
        """Detect themes in content."""
        try:
            # Use underlying methods if available
            if hasattr(self._analyzer, 'detect_themes'):
                return await self._analyzer.detect_themes(content)
            else:
                # Fallback implementation
                return ["general"]
        except (RuntimeError, AttributeError, OSError, ValueError, KeyError, TypeError) as e:
            log_warning(f"detect_content_themes failed: {e}")
            return []

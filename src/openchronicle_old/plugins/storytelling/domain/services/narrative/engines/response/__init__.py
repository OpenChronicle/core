"""
OpenChronicle Core - Response Intelligence System

Modular response intelligence system providing context analysis,
response planning, and quality evaluation.

Replaces IntelligentResponseEngine (995 lines) with specialized components.

Author: OpenChronicle Development Team
"""

from .context_analyzer import ContextAnalyzer
from .response_models import (
    ContextAnalysis,
    ContextQuality,
    ResponseComplexity,
    ResponseContext,
    ResponseEvaluation,
    ResponseMetrics,
    ResponsePlan,
    ResponseRequest,
    ResponseResult,
    ResponseStrategy,
)
from .response_orchestrator import ResponseOrchestrator
from .response_planner import ResponsePlanner

__all__ = [
    # Core orchestrator
    "ResponseOrchestrator",
    # Component classes
    "ContextAnalyzer",
    "ResponsePlanner",
    # Data models
    "ResponseStrategy",
    "ContextQuality",
    "ResponseComplexity",
    "ContextAnalysis",
    "ResponsePlan",
    "ResponseEvaluation",
    "ResponseMetrics",
    "ResponseContext",
    "ResponseRequest",
    "ResponseResult",
]

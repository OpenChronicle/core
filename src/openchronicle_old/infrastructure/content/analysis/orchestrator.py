"""
Content Analysis Orchestrator (removed)

The core ContentAnalysisOrchestrator has been removed. Content analysis is now
exposed via domain ports and plugin-owned implementations. Use
IContentAnalysisPort from the domain layer and resolve an implementation via the
DI container or a plugin facade.
"""

raise ImportError(
    "ContentAnalysisOrchestrator has been removed from core. Resolve an "
    "IContentAnalysisPort via plugins/DI (e.g., storytelling plugin)."
)

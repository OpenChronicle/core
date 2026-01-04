"""Deprecated core ContentAnalysisAdapter.

Content analysis is provided via plugin-owned implementations of the domain
port `IContentAnalysisPort`. Import adapters from plugins (e.g., storytelling)
instead.
"""

raise ImportError("Core ContentAnalysisAdapter removed. Resolve IContentAnalysisPort via plugin adapters.")

"""TEMP re-export during migration to plugin-based architecture.

This module exposes the ContextAnalyzer from the storytelling plugin to
preserve import compatibility during Phase 1.
"""

from openchronicle.domain.services.narrative import *  # type: ignore # noqa: F401,F403

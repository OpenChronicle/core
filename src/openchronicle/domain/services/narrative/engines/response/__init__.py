"""TEMP re-export during migration to plugin-based architecture.

This module exposes response intelligence components from the storytelling plugin to
preserve import compatibility during Phase 1.
"""

# Import from the main narrative shim instead of directly from plugin
from openchronicle.domain.services.narrative import *  # type: ignore # noqa: F401,F403

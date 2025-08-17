"""TEMP re-export during migration to plugin-based architecture.

This module exposes narrative mechanics handler from the storytelling plugin to
preserve import compatibility during Phase 1.
"""

# Import via the domain shim to avoid direct plugin dependency
from openchronicle.domain.services.narrative import *  # type: ignore # noqa: F401,F403

"""Story Loader Shim (plugin-agnostic).

All story loading logic lives in domain-specific plugins (e.g., storytelling).
Core no longer re-exports plugin implementations. Use the plugin's own
APIs or resolve through dependency injection.

This module intentionally provides no runtime functionality to avoid
plugin coupling from the core domain.
"""

__all__: list[str] = []

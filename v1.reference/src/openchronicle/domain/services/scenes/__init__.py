"""Scenes Service Shim (plugin-agnostic).

Scene-related services are implemented by plugins. The core domain no longer
re-exports plugin implementations. Resolve via plugin package or DI.
"""

__all__: list[str] = []

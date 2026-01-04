"""Characters Service Shim (plugin-agnostic).

Character-related services are provided by plugins. The core domain does not
re-export plugin implementations. Access them via the plugin package or DI.
"""

__all__: list[str] = []

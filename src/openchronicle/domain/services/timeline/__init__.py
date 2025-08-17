"""Timeline Service Shim (plugin-agnostic).

Timeline orchestration/services are provided by plugins. Core does not
re-export plugin implementations. Use plugin APIs or DI to resolve them.
"""

__all__: list[str] = []

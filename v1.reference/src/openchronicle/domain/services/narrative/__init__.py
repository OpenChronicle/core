"""Narrative Service Shim (plugin-agnostic).

Narrative engines and services live in plugins. Core does not re-export
plugin implementations. Resolve narrative services via plugins or DI.
"""

__all__: list[str] = []

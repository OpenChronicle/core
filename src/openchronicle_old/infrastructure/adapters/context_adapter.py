"""Deprecated core ContextAdapter.

Context building is provided via plugin-owned implementations of the domain
port `IContextPort`. Import adapters from plugins (e.g., storytelling) instead.
"""

raise ImportError("Core ContextAdapter removed. Resolve IContextPort via plugin adapters.")

"""MCP server configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, cast


@dataclass(frozen=True)
class MCPConfig:
    """Immutable MCP server configuration.

    Three-layer precedence: env var > file config (core.json mcp section) > default.

    Env vars:
        OC_MCP_TRANSPORT — "stdio" or "sse" (default: "stdio")
        OC_MCP_HOST — bind address for SSE transport (default: "127.0.0.1")
        OC_MCP_PORT — port for SSE transport (default: 8080)
    """

    transport: Literal["stdio", "sse"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8080
    server_name: str = "openchronicle"

    @classmethod
    def from_env(cls, file_config: dict[str, object] | None = None) -> MCPConfig:
        """Load config from environment variables with file_config fallback."""
        fc = file_config or {}

        transport = os.environ.get("OC_MCP_TRANSPORT", "").strip() or _str_or_default(fc.get("transport"), "stdio")
        if transport not in ("stdio", "sse"):
            raise ValueError(f"Invalid MCP transport: {transport!r}. Must be 'stdio' or 'sse'.")

        host = os.environ.get("OC_MCP_HOST", "").strip() or _str_or_default(fc.get("host"), "127.0.0.1")

        port_env = os.environ.get("OC_MCP_PORT", "").strip()
        port_file = fc.get("port")
        if port_env:
            port = int(port_env)
        elif isinstance(port_file, int):
            port = port_file
        else:
            port = 8080

        server_name = _str_or_default(fc.get("server_name"), "openchronicle")

        return cls(transport=cast(Literal["stdio", "sse"], transport), host=host, port=port, server_name=server_name)


def _str_or_default(value: object, default: str) -> str:
    """Return value as str if truthy, else default."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default

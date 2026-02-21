"""CLI commands for the MCP server (oc mcp serve)."""

from __future__ import annotations

import argparse
import logging
import sys

from openchronicle.core.infrastructure.wiring.container import CoreContainer


def cmd_mcp(args: argparse.Namespace, container: CoreContainer) -> int:
    """Dispatch mcp subcommands."""
    sub = getattr(args, "mcp_command", None)
    if sub == "serve":
        return _cmd_mcp_serve(args, container)
    print("Usage: oc mcp serve")
    return 0


def _cmd_mcp_serve(args: argparse.Namespace, container: CoreContainer) -> int:
    """Start the MCP server."""
    try:
        import mcp  # noqa: F401
    except ImportError:
        print("mcp SDK is not installed. Install with: pip install -e '.[mcp]'", file=sys.stderr)
        return 1

    from openchronicle.interfaces.mcp.config import MCPConfig
    from openchronicle.interfaces.mcp.server import create_server

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    transport = getattr(args, "transport", None) or "stdio"
    host = getattr(args, "host", None) or "127.0.0.1"
    port = getattr(args, "port", None) or 8080

    # CLI args override env/file config for transport/host/port
    import os

    if transport:
        os.environ["OC_MCP_TRANSPORT"] = transport
    if getattr(args, "host", None):
        os.environ["OC_MCP_HOST"] = host
    if getattr(args, "port", None):
        os.environ["OC_MCP_PORT"] = str(port)

    try:
        config = MCPConfig.from_env(file_config=container.file_configs.get("mcp"))
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    server = create_server(container, config)

    print(f"Starting MCP server (transport={config.transport})")
    server.run(transport=config.transport)
    return 0

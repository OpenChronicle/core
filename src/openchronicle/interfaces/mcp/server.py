"""MCP server factory — creates and configures a FastMCP instance."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.mcp.config import MCPConfig

logger = logging.getLogger(__name__)


def create_server(container: CoreContainer, config: MCPConfig) -> FastMCP:
    """Build a fully-wired FastMCP server with all OC tools registered.

    The container is injected into tool handlers via the lifespan context.
    Tools access it as ``ctx.request_context.lifespan_context["container"]``.
    """

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        logger.info("OpenChronicle MCP server starting")
        yield {"container": container}
        logger.info("OpenChronicle MCP server shutting down")

    mcp = FastMCP(
        config.server_name,
        instructions=(
            "OpenChronicle provides durable memory and conversation capabilities "
            "across sessions. Use memory tools to store and retrieve knowledge. "
            "Use conversation tools to interact through OC's full LLM pipeline."
        ),
        lifespan=lifespan,
        host=config.host,
        port=config.port,
    )

    # Register tool modules
    from openchronicle.interfaces.mcp.tools import asset, context, conversation, memory, onboard, project, system

    system.register(mcp)
    project.register(mcp)
    memory.register(mcp)
    conversation.register(mcp)
    context.register(mcp)
    onboard.register(mcp)
    asset.register(mcp)

    return mcp

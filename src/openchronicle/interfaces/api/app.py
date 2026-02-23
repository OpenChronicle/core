"""FastAPI app factory — creates and configures the HTTP API server."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.api.config import HTTPConfig

logger = logging.getLogger(__name__)


def create_app(container: CoreContainer, config: HTTPConfig) -> FastAPI:
    """Build a fully-wired FastAPI application with all OC routes registered.

    The container is stored eagerly in ``app.state`` so route handlers
    can access it immediately via dependency injection.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info("OpenChronicle HTTP API starting on %s:%d", config.host, config.port)
        yield
        logger.info("OpenChronicle HTTP API shutting down")

    app = FastAPI(
        title="OpenChronicle",
        description=(
            "Durable context engine for LLM interactions — persistent memory, "
            "explainable routing, and auditable decision trails."
        ),
        version="2.0.0",
        lifespan=lifespan,
    )

    # Eagerly set container + config on app state so route handlers can
    # access them immediately (works with both real server and TestClient).
    app.state.container = container
    app.state.http_config = config

    # Register middleware
    from openchronicle.interfaces.api.middleware import register_middleware

    register_middleware(app, config)

    # Register route modules
    from openchronicle.interfaces.api.routes import (
        asset,
        conversation,
        memory,
        project,
        system,
    )

    app.include_router(system.router, prefix="/api/v1", tags=["system"])
    app.include_router(project.router, prefix="/api/v1", tags=["project"])
    app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
    app.include_router(conversation.router, prefix="/api/v1", tags=["conversation"])
    app.include_router(asset.router, prefix="/api/v1", tags=["asset"])

    return app

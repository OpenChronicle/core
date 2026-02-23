"""FastAPI dependency injection — container access for route handlers."""

from __future__ import annotations

from fastapi import Request

from openchronicle.core.infrastructure.wiring.container import CoreContainer


def get_container(request: Request) -> CoreContainer:
    """Retrieve the CoreContainer from app state.

    Usage in route handlers::

        @router.get("/api/v1/health")
        def health(container: CoreContainer = Depends(get_container)):
            ...
    """
    return request.app.state.container  # type: ignore[no-any-return]

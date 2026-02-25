"""Webhook tools — register, list, delete."""

from __future__ import annotations

from typing import Any, cast

from mcp.server.fastmcp import Context, FastMCP

from openchronicle.core.application.use_cases import delete_webhook, list_webhooks, register_webhook
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.mcp.tracking import track_tool
from openchronicle.interfaces.serializers import webhook_to_dict


def _get_container(ctx: Context) -> CoreContainer:
    return cast(CoreContainer, ctx.request_context.lifespan_context["container"])


def register(mcp: FastMCP) -> None:
    """Register webhook tools on the MCP server."""

    @mcp.tool()
    @track_tool
    def webhook_register(
        project_id: str,
        url: str,
        ctx: Context,
        event_filter: str = "*",
        description: str = "",
    ) -> dict[str, Any]:
        """Register a new webhook subscription.

        Args:
            project_id: Project to associate the webhook with.
            url: Target endpoint URL (must start with http:// or https://).
            event_filter: Glob pattern for event types (default: "*" for all).
            description: Optional human-readable description.
        """
        if not url or len(url) > 2048:
            raise ValueError("URL must be non-empty and <= 2048 characters")
        container = _get_container(ctx)
        sub = register_webhook.execute(
            webhook_service=container.webhook_service,
            emit_event=container.emit_event,
            project_id=project_id,
            url=url,
            event_filter=event_filter or "*",
            description=description or "",
        )
        container.ensure_webhook_dispatcher()
        return webhook_to_dict(sub)

    @mcp.tool()
    @track_tool
    def webhook_list(
        ctx: Context,
        project_id: str | None = None,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        """List webhook subscriptions.

        Args:
            project_id: Optional project filter.
            active_only: If true, only return active subscriptions.
        """
        container = _get_container(ctx)
        result = list_webhooks.execute(
            webhook_service=container.webhook_service,
            project_id=project_id,
            active_only=active_only,
        )
        return [webhook_to_dict(s) for s in result]

    @mcp.tool()
    @track_tool
    def webhook_delete(
        webhook_id: str,
        ctx: Context,
    ) -> dict[str, Any]:
        """Delete a webhook subscription.

        Args:
            webhook_id: The ID of the webhook subscription to delete.
        """
        if not webhook_id:
            raise ValueError("webhook_id must not be empty")
        container = _get_container(ctx)
        delete_webhook.execute(
            webhook_service=container.webhook_service,
            emit_event=container.emit_event,
            subscription_id=webhook_id,
        )
        return {"deleted": webhook_id}

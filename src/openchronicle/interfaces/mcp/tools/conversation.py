"""Conversation tools — create, list, history, ask."""

from __future__ import annotations

from typing import Any, cast

from mcp.server.fastmcp import Context, FastMCP

from openchronicle.core.application.use_cases import (
    ask_conversation,
    create_conversation,
    list_conversations,
    show_conversation,
)
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.mcp.tracking import track_tool
from openchronicle.interfaces.serializers import conversation_to_dict, turn_to_dict


def _get_container(ctx: Context) -> CoreContainer:
    return cast(CoreContainer, ctx.request_context.lifespan_context["container"])


def register(mcp: FastMCP) -> None:
    """Register conversation tools on the MCP server."""

    @mcp.tool()
    @track_tool
    def conversation_create(
        ctx: Context,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Create a new conversation.

        Args:
            title: Optional title for the conversation.
        """
        container = _get_container(ctx)
        convo = create_conversation.execute(
            storage=container.storage,
            convo_store=container.storage,
            emit_event=container.event_logger.append,
            title=title,
        )
        return conversation_to_dict(convo)

    @mcp.tool()
    @track_tool
    def conversation_list(
        ctx: Context,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """List conversations, most recent first.

        Args:
            limit: Maximum number of conversations to return (None for all).
        """
        container = _get_container(ctx)
        convos = list_conversations.execute(
            convo_store=container.storage,
            limit=limit,
        )
        return [conversation_to_dict(c) for c in convos]

    @mcp.tool()
    @track_tool
    def conversation_history(
        conversation_id: str,
        ctx: Context,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve the turn history for a conversation.

        Args:
            conversation_id: The conversation to retrieve.
            limit: Maximum number of turns to return (None for all).
        """
        container = _get_container(ctx)
        convo, turns = show_conversation.execute(
            convo_store=container.storage,
            conversation_id=conversation_id,
            limit=limit,
        )
        return {
            "conversation": conversation_to_dict(convo),
            "turns": [turn_to_dict(t) for t in turns],
        }

    @mcp.tool()
    @track_tool
    async def conversation_ask(
        conversation_id: str,
        prompt: str,
        ctx: Context,
        moe: bool = False,
    ) -> dict[str, Any]:
        """Send a message through OpenChronicle's full pipeline.

        Routes through memory retrieval, privacy gate, provider selection,
        LLM call, turn persistence, and event logging. Non-streaming.

        Args:
            conversation_id: The conversation to continue.
            prompt: The user message to send.
            moe: Use Mixture-of-Experts consensus mode.
        """
        container = _get_container(ctx)
        turn = await ask_conversation.execute(
            convo_store=container.storage,
            storage=container.storage,
            memory_store=container.storage,
            llm=container.llm,
            emit_event=container.event_logger.append,
            conversation_id=conversation_id,
            prompt_text=prompt,
            interaction_router=container.interaction_router,
            router_policy=container.router_policy,
            allow_pii=False,
            privacy_gate=container.privacy_gate,
            privacy_settings=container.privacy_settings,
            moe=moe,
        )
        return turn_to_dict(turn)

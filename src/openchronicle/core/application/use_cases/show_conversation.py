from __future__ import annotations

from openchronicle.core.domain.models.conversation import Conversation, Turn
from openchronicle.core.domain.ports.conversation_store_port import ConversationStorePort


def execute(
    convo_store: ConversationStorePort,
    conversation_id: str,
    limit: int | None = None,
) -> tuple[Conversation, list[Turn]]:
    conversation = convo_store.get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation not found: {conversation_id}")

    turns = convo_store.list_turns(conversation_id, limit=limit)
    return conversation, turns

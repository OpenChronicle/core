from __future__ import annotations

from collections.abc import Callable

from openchronicle.core.domain.models.conversation import Conversation
from openchronicle.core.domain.models.project import Event, Project
from openchronicle.core.domain.ports.conversation_store_port import ConversationStorePort
from openchronicle.core.domain.ports.storage_port import StoragePort


def execute(
    storage: StoragePort,
    convo_store: ConversationStorePort,
    emit_event: Callable[[Event], None],
    title: str | None = None,
) -> Conversation:
    conversation_title = title or ""

    project = Project(name="conversation", metadata={"type": "conversation", "title": conversation_title})
    storage.add_project(project)

    conversation = Conversation(project_id=project.id, title=conversation_title)
    convo_store.add_conversation(conversation)

    emit_event(
        Event(
            project_id=project.id,
            task_id=conversation.id,
            type="convo.created",
            payload={"conversation_id": conversation.id, "title": conversation.title},
        )
    )

    return conversation

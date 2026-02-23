"""Memory routes — search, save, list, pin."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from openchronicle.core.application.use_cases import add_memory, list_memory, pin_memory, search_memory
from openchronicle.core.domain.models.memory_item import MemoryItem
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.api.deps import get_container
from openchronicle.interfaces.serializers import memory_to_dict

router = APIRouter(prefix="/memory")

ContainerDep = Annotated[CoreContainer, Depends(get_container)]


@router.get("/search")
def memory_search(
    container: ContainerDep,
    query: str,
    top_k: int = 8,
    conversation_id: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    """Search memory items by keyword."""
    results = search_memory.execute(
        store=container.storage,
        query=query,
        top_k=top_k,
        conversation_id=conversation_id,
        project_id=project_id,
    )
    return [memory_to_dict(m) for m in results]


class MemorySaveRequest(BaseModel):
    content: str
    tags: list[str] | None = None
    pinned: bool = False
    conversation_id: str | None = None
    project_id: str | None = None
    created_at: str | None = None


@router.post("")
def memory_save(
    body: MemorySaveRequest,
    container: ContainerDep,
) -> dict[str, Any]:
    """Save a memory item for persistent retrieval across sessions."""
    # Derive project_id from conversation if needed
    resolved_project_id = body.project_id
    if resolved_project_id is None and body.conversation_id:
        convo = container.storage.get_conversation(body.conversation_id)
        if convo is None:
            raise HTTPException(status_code=404, detail=f"Conversation not found: {body.conversation_id}")
        resolved_project_id = convo.project_id

    if not resolved_project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id is required (provide directly or via conversation_id)",
        )

    kwargs: dict[str, Any] = {
        "content": body.content,
        "tags": body.tags or [],
        "pinned": body.pinned,
        "conversation_id": body.conversation_id,
        "project_id": resolved_project_id,
        "source": "api",
    }
    if body.created_at is not None:
        kwargs["created_at"] = datetime.fromisoformat(body.created_at)
    item = MemoryItem(**kwargs)
    saved = add_memory.execute(
        store=container.storage,
        emit_event=container.event_logger.append,
        item=item,
    )
    return memory_to_dict(saved)


@router.get("")
def memory_list(
    container: ContainerDep,
    limit: int | None = None,
    pinned_only: bool = False,
) -> list[dict[str, Any]]:
    """List memory items."""
    results = list_memory.execute(
        store=container.storage,
        limit=limit,
        pinned_only=pinned_only,
    )
    return [memory_to_dict(m) for m in results]


class MemoryPinRequest(BaseModel):
    pinned: bool = True


@router.put("/{memory_id}/pin")
def memory_pin(
    memory_id: str,
    body: MemoryPinRequest,
    container: ContainerDep,
) -> dict[str, str]:
    """Pin or unpin a memory item."""
    pin_memory.execute(
        store=container.storage,
        emit_event=container.event_logger.append,
        memory_id=memory_id,
        pinned=body.pinned,
    )
    return {"status": "ok", "memory_id": memory_id, "pinned": str(body.pinned)}

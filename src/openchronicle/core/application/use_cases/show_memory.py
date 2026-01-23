from __future__ import annotations

from openchronicle.core.domain.models.memory_item import MemoryItem
from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort


def execute(store: MemoryStorePort, memory_id: str) -> MemoryItem:
    memory = store.get_memory(memory_id)
    if memory is None:
        raise ValueError(f"Memory not found: {memory_id}")
    return memory

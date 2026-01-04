from __future__ import annotations

import asyncio
from typing import Any

from openchronicle_core.core.domain.models.project import Task  # type: ignore[import]
from openchronicle_core.core.domain.ports.plugin_port import PluginRegistry  # type: ignore[import]


async def _story_draft_handler(task: Task, *, context: dict[str, Any] | None = None) -> str:
    await asyncio.sleep(0)
    prompt = task.payload.get("prompt") or "Tell a short story."
    return f"[storytelling draft] {prompt}"


def register(registry: PluginRegistry) -> None:
    registry.register_task_handler("story.draft", _story_draft_handler)
    registry.register_agent_template({"role": "storyteller", "description": "Generates narrative drafts."})

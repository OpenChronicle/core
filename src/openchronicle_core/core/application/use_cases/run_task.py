from __future__ import annotations

from typing import Any

from openchronicle_core.core.domain.models.project import Task
from openchronicle_core.core.domain.services.orchestrator import OrchestratorService


def submit(orchestrator: OrchestratorService, project_id: str, task_type: str, payload: dict[str, Any]) -> Task:
    return orchestrator.submit_task(project_id=project_id, task_type=task_type, payload=payload)


async def execute(orchestrator: OrchestratorService, task_id: str, agent_id: str | None = None) -> str:
    return await orchestrator.execute_task(task_id=task_id, agent_id=agent_id)

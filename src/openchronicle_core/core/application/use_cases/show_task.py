from __future__ import annotations

from openchronicle_core.core.domain.services.orchestrator import OrchestratorService


def timeline(orchestrator: OrchestratorService, task_id: str):
    return orchestrator.storage.list_events(task_id)

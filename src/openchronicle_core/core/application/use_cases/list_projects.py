from __future__ import annotations

from openchronicle_core.core.domain.services.orchestrator import OrchestratorService


def execute(orchestrator: OrchestratorService):
    return orchestrator.storage.list_projects()

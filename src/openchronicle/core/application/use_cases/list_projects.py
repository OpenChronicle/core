from __future__ import annotations

from openchronicle.core.domain.models.project import Project
from openchronicle.core.domain.services.orchestrator import OrchestratorService


def execute(orchestrator: OrchestratorService) -> list[Project]:
    return orchestrator.storage.list_projects()

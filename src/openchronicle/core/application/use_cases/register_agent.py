from __future__ import annotations

from openchronicle.core.domain.models.project import Agent
from openchronicle.core.domain.services.orchestrator import OrchestratorService


def execute(
    orchestrator: OrchestratorService,
    project_id: str,
    name: str,
    role: str = "worker",
    provider: str = "",
    model: str = "",
    tags: list[str] | None = None,
) -> Agent:
    return orchestrator.register_agent(
        project_id=project_id,
        name=name,
        role=role,
        provider=provider,
        model=model,
        tags=tags,
    )

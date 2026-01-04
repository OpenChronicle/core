from __future__ import annotations

from typing import Any

from openchronicle_core.core.domain.services.orchestrator import OrchestratorService


def execute(
    orchestrator: OrchestratorService,
    project_id: str,
    name: str,
    role: str = "worker",
    provider: str = "",
    model: str = "",
    tags: list[str] | None = None,
):
    return orchestrator.register_agent(
        project_id=project_id,
        name=name,
        role=role,
        provider=provider,
        model=model,
        tags=tags,
    )

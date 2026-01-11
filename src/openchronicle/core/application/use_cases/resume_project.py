"""Resume project use case - transitions orphaned RUNNING tasks back to PENDING."""

from __future__ import annotations

from dataclasses import dataclass

from openchronicle.core.application.services.orchestrator import OrchestratorService
from openchronicle.core.domain.models.project import Event, TaskStatus


@dataclass
class ResumeSummary:
    """Summary of resume operation."""

    project_id: str
    orphaned_to_pending: int
    pending: int
    running: int
    completed: int
    failed: int


def execute(orchestrator: OrchestratorService, project_id: str) -> ResumeSummary:
    """
    Resume a project by identifying and handling interrupted tasks.

    This operation is idempotent:
    - Only acts on tasks currently in RUNNING status
    - Transitions them to PENDING with explicit task.orphaned event
    - Emits project.resumed event with summary counts

    Args:
        orchestrator: Orchestrator service with storage access
        project_id: Project ID to resume

    Returns:
        ResumeSummary with counts of tasks by status after resume
    """
    storage = orchestrator.storage
    tasks = storage.list_tasks_by_project(project_id)

    # Sort deterministically by created_at, then id
    tasks_sorted = sorted(tasks, key=lambda t: (t.created_at, t.id))

    # Identify interrupted tasks (currently RUNNING)
    interrupted = [t for t in tasks_sorted if t.status == TaskStatus.RUNNING]

    # Transition each interrupted task to PENDING with explicit event
    for task in interrupted:
        # Emit task.orphaned event explaining the transition
        storage.append_event(
            Event(
                project_id=project_id,
                task_id=task.id,
                agent_id=task.agent_id,
                type="task.orphaned",
                payload={
                    "task_id": task.id,
                    "task_type": task.type,
                    "previous_status": "running",
                    "resume_policy": "restart_running",
                    "reason": "Task was running when application stopped; restarting from scratch",
                },
            )
        )

        # Transition to PENDING
        storage.update_task_status(task.id, TaskStatus.PENDING.value)

    # Count final status distribution
    # Re-fetch tasks to get updated statuses
    tasks_after = storage.list_tasks_by_project(project_id)
    counts = {
        "pending": sum(1 for t in tasks_after if t.status == TaskStatus.PENDING),
        "running": sum(1 for t in tasks_after if t.status == TaskStatus.RUNNING),
        "completed": sum(1 for t in tasks_after if t.status == TaskStatus.COMPLETED),
        "failed": sum(1 for t in tasks_after if t.status == TaskStatus.FAILED),
    }

    # Emit project.resumed event with summary
    storage.append_event(
        Event(
            project_id=project_id,
            task_id=None,
            agent_id=None,
            type="project.resumed",
            payload={
                "project_id": project_id,
                "orphaned_to_pending": len(interrupted),
                "pending": counts["pending"],
                "running": counts["running"],
                "completed": counts["completed"],
                "failed": counts["failed"],
                "total_tasks": len(tasks_after),
            },
        )
    )

    return ResumeSummary(
        project_id=project_id,
        orphaned_to_pending=len(interrupted),
        pending=counts["pending"],
        running=counts["running"],
        completed=counts["completed"],
        failed=counts["failed"],
    )

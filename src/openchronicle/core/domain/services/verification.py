"""Hash-chain verification service for event integrity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openchronicle.core.domain.ports.storage_port import StoragePort


@dataclass
class VerificationResult:
    """Result of hash-chain verification."""

    success: bool
    total_events: int
    verified_events: int
    first_mismatch: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass
class ProjectVerificationResult:
    """Result of project-wide verification."""

    success: bool
    total_tasks: int
    passed_tasks: int
    failed_tasks: int
    failures: list[dict[str, Any]]  # List of failed task details


class VerificationService:
    """Verifies the integrity of event hash chains."""

    def __init__(self, storage: StoragePort) -> None:
        self.storage = storage

    def verify_task_chain(self, task_id: str) -> VerificationResult:
        """
        Verify the hash chain for all events in a task.

        Returns:
            VerificationResult with success status and details of any mismatch.
        """
        events = self.storage.list_events(task_id)

        if not events:
            return VerificationResult(
                success=True, total_events=0, verified_events=0, error_message="No events found for task"
            )

        total = len(events)
        verified = 0
        prev_hash = None

        for idx, event in enumerate(events):
            # Verify prev_hash linkage
            if event.prev_hash != prev_hash:
                return VerificationResult(
                    success=False,
                    total_events=total,
                    verified_events=verified,
                    first_mismatch={
                        "event_index": idx,
                        "event_id": event.id,
                        "event_type": event.type,
                        "expected_prev_hash": prev_hash,
                        "actual_prev_hash": event.prev_hash,
                    },
                    error_message=f"prev_hash mismatch at event {idx} (type={event.type})",
                )

            # Recompute hash and verify (without mutating stored hash)
            stored_hash = event.hash
            computed_hash = event.calculate_hash()
            if computed_hash != stored_hash:
                return VerificationResult(
                    success=False,
                    total_events=total,
                    verified_events=verified,
                    first_mismatch={
                        "event_index": idx,
                        "event_id": event.id,
                        "event_type": event.type,
                        "expected_hash": stored_hash,
                        "computed_hash": computed_hash,
                    },
                    error_message=f"Hash mismatch at event {idx} (type={event.type})",
                )

            verified += 1
            prev_hash = event.hash

        return VerificationResult(success=True, total_events=total, verified_events=verified)

    def verify_project(self, project_id: str) -> ProjectVerificationResult:
        """
        Verify hash chains for all tasks in a project.

        Returns:
            ProjectVerificationResult with summary of verification status.
        """
        tasks = self.storage.list_tasks_by_project(project_id)

        if not tasks:
            return ProjectVerificationResult(success=True, total_tasks=0, passed_tasks=0, failed_tasks=0, failures=[])

        total = len(tasks)
        passed = 0
        failures = []

        for task in tasks:
            result = self.verify_task_chain(task.id)
            if result.success:
                passed += 1
            else:
                failures.append(
                    {
                        "task_id": task.id,
                        "task_type": task.type,
                        "error_message": result.error_message,
                        "first_mismatch_event_id": result.first_mismatch.get("event_id")
                        if result.first_mismatch
                        else None,
                        "first_mismatch_index": result.first_mismatch.get("event_index")
                        if result.first_mismatch
                        else None,
                    }
                )

        failed = total - passed
        return ProjectVerificationResult(
            success=(failed == 0), total_tasks=total, passed_tasks=passed, failed_tasks=failed, failures=failures
        )

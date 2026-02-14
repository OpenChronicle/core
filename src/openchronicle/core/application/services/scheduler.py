"""Scheduler service — tick-driven job execution via orchestrator.

The scheduler polls for due jobs and submits them as tasks. It does not
execute tasks itself. Jobs persist in SQLite. `tick()` is sync (DB only);
`serve()` is async (polling loop with clean shutdown).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from openchronicle.core.domain.models.project import Event, Task
from openchronicle.core.domain.models.scheduled_job import JobStatus, ScheduledJob
from openchronicle.core.domain.ports.storage_port import StoragePort

_logger = logging.getLogger(__name__)


class SchedulerError(Exception):
    """Base error for scheduler operations."""


class JobNotFoundError(SchedulerError):
    """Raised when a job_id does not exist."""


class InvalidTransitionError(SchedulerError):
    """Raised when a state transition is not allowed."""


# Terminal states — no further transitions allowed
_TERMINAL = frozenset({JobStatus.COMPLETED, JobStatus.CANCELLED})


class SchedulerService:
    """Tick-driven job scheduler.

    Dependencies:
        storage: StoragePort for job persistence
        submit_task: callable that creates a Task (OrchestratorService.submit_task)
        emit_event: callable that appends a hash-chained Event
    """

    def __init__(
        self,
        storage: StoragePort,
        submit_task: Callable[..., Task],
        emit_event: Callable[[Event], None],
    ) -> None:
        self._storage = storage
        self._submit_task = submit_task
        self._emit_event = emit_event

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def add_job(
        self,
        project_id: str,
        name: str,
        task_type: str,
        task_payload: dict[str, Any],
        *,
        due_at: datetime | None = None,
        interval_seconds: int | None = None,
        max_failures: int = 0,
    ) -> ScheduledJob:
        job = ScheduledJob(
            project_id=project_id,
            name=name,
            task_type=task_type,
            task_payload=task_payload,
            next_due_at=due_at or datetime.now(UTC),
            interval_seconds=interval_seconds,
            max_failures=max_failures,
        )
        self._storage.add_scheduled_job(job)
        self._emit_event(
            Event(
                project_id=project_id,
                type="scheduler.job_created",
                payload={
                    "job_id": job.id,
                    "name": name,
                    "task_type": task_type,
                    "interval_seconds": interval_seconds,
                    "next_due_at": job.next_due_at.isoformat(),
                },
            )
        )
        return job

    def pause_job(self, job_id: str) -> ScheduledJob:
        job = self._get_or_raise(job_id)
        if job.status != JobStatus.ACTIVE:
            raise InvalidTransitionError(f"Cannot pause job {job_id}: status is {job.status.value}, expected active")
        self._storage.update_scheduled_job_status(job_id, JobStatus.PAUSED.value)
        self._emit_event(
            Event(
                project_id=job.project_id,
                type="scheduler.job_paused",
                payload={"job_id": job_id},
            )
        )
        job.status = JobStatus.PAUSED
        return job

    def resume_job(self, job_id: str) -> ScheduledJob:
        job = self._get_or_raise(job_id)
        if job.status != JobStatus.PAUSED:
            raise InvalidTransitionError(f"Cannot resume job {job_id}: status is {job.status.value}, expected paused")
        self._storage.update_scheduled_job_status(job_id, JobStatus.ACTIVE.value)
        self._emit_event(
            Event(
                project_id=job.project_id,
                type="scheduler.job_resumed",
                payload={"job_id": job_id},
            )
        )
        job.status = JobStatus.ACTIVE
        return job

    def cancel_job(self, job_id: str) -> ScheduledJob:
        job = self._get_or_raise(job_id)
        if job.status in _TERMINAL:
            raise InvalidTransitionError(f"Cannot cancel job {job_id}: already in terminal state {job.status.value}")
        self._storage.update_scheduled_job_status(job_id, JobStatus.CANCELLED.value)
        self._emit_event(
            Event(
                project_id=job.project_id,
                type="scheduler.job_cancelled",
                payload={"job_id": job_id},
            )
        )
        job.status = JobStatus.CANCELLED
        return job

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_jobs(self, project_id: str | None = None, status: str | None = None) -> list[ScheduledJob]:
        return self._storage.list_scheduled_jobs(project_id=project_id, status=status)

    def get_job(self, job_id: str) -> ScheduledJob:
        return self._get_or_raise(job_id)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, now: datetime | None = None, max_jobs: int = 10) -> list[tuple[ScheduledJob, Task]]:
        """Poll for due jobs, submit tasks, return (job, task) pairs."""
        if now is None:
            now = datetime.now(UTC)

        claimed = self._storage.claim_due_jobs(now, max_jobs=max_jobs)
        results: list[tuple[ScheduledJob, Task]] = []

        t0 = time.monotonic()

        for job in claimed:
            payload = dict(job.task_payload)
            payload["_scheduler_job_id"] = job.id

            task = self._submit_task(
                project_id=job.project_id,
                task_type=job.task_type,
                payload=payload,
            )

            self._storage.update_scheduled_job_last_task(job.id, task.id)
            job.last_task_id = task.id

            self._emit_event(
                Event(
                    project_id=job.project_id,
                    type="scheduler.job_fired",
                    payload={
                        "job_id": job.id,
                        "task_id": task.id,
                        "fire_count": job.fire_count,
                        "task_type": job.task_type,
                    },
                )
            )
            results.append((job, task))

        elapsed = time.monotonic() - t0

        # Emit tick summary. Use first claimed job's project for the event
        # chain; skip if no jobs were claimed (no project context).
        if results:
            self._emit_event(
                Event(
                    project_id=results[0][0].project_id,
                    type="scheduler.tick_completed",
                    payload={
                        "jobs_fired": len(results),
                        "tick_time": round(elapsed, 4),
                    },
                )
            )

        return results

    # ------------------------------------------------------------------
    # Serve (async polling loop)
    # ------------------------------------------------------------------

    async def serve(
        self,
        poll_interval: float = 60.0,
        max_jobs_per_tick: int = 10,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Run the scheduler polling loop until stop_event is set."""
        if stop_event is None:
            stop_event = asyncio.Event()

        _logger.info("Scheduler serve started (interval=%.1fs)", poll_interval)

        while not stop_event.is_set():
            try:
                results = self.tick(max_jobs=max_jobs_per_tick)
                if results:
                    _logger.info("Scheduler tick: %d jobs fired", len(results))
            except Exception:
                _logger.exception("Scheduler tick failed")

            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)

        _logger.info("Scheduler serve stopped")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_raise(self, job_id: str) -> ScheduledJob:
        job = self._storage.get_scheduled_job(job_id)
        if job is None:
            raise JobNotFoundError(f"Scheduled job not found: {job_id}")
        return job

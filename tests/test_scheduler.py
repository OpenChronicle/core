"""Tests for SchedulerService."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from openchronicle.core.application.services.scheduler import (
    InvalidTransitionError,
    JobNotFoundError,
    SchedulerService,
)
from openchronicle.core.domain.models.project import Event, Project, Task
from openchronicle.core.domain.models.scheduled_job import JobStatus
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> SqliteStore:
    s = SqliteStore(str(tmp_path / "sched.db"))
    s.init_schema()
    s.add_project(Project(id="proj-1", name="test"))
    return s


class _FakeOrchestrator:
    """Captures submit_task calls and returns predictable Tasks."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._counter = 0

    def submit_task(self, **kwargs: Any) -> Task:
        self._counter += 1
        task = Task(
            id=f"task-{self._counter}",
            project_id=kwargs["project_id"],
            type=kwargs["task_type"],
            payload=kwargs["payload"],
        )
        self.calls.append(kwargs)
        return task


@pytest.fixture()
def orchestrator() -> _FakeOrchestrator:
    return _FakeOrchestrator()


@pytest.fixture()
def events() -> list[Event]:
    return []


@pytest.fixture()
def scheduler(store: SqliteStore, orchestrator: _FakeOrchestrator, events: list[Event]) -> SchedulerService:
    return SchedulerService(
        storage=store,
        submit_task=orchestrator.submit_task,
        emit_event=events.append,
    )


# ---------------------------------------------------------------------------
# Job creation
# ---------------------------------------------------------------------------


class TestAddJob:
    def test_one_shot_job(self, scheduler: SchedulerService, events: list[Event]) -> None:
        job = scheduler.add_job(
            project_id="proj-1",
            name="once",
            task_type="plugin.invoke",
            task_payload={"handler": "hello.echo"},
        )
        assert job.status == JobStatus.ACTIVE
        assert job.interval_seconds is None
        assert job.fire_count == 0
        assert any(e.type == "scheduler.job_created" for e in events)

    def test_recurring_job(self, scheduler: SchedulerService) -> None:
        job = scheduler.add_job(
            project_id="proj-1",
            name="recurring",
            task_type="plugin.invoke",
            task_payload={"handler": "scan.run"},
            interval_seconds=300,
        )
        assert job.interval_seconds == 300

    def test_custom_due_at(self, scheduler: SchedulerService) -> None:
        future = datetime.now(UTC) + timedelta(hours=1)
        job = scheduler.add_job(
            project_id="proj-1",
            name="later",
            task_type="plugin.invoke",
            task_payload={},
            due_at=future,
        )
        assert job.next_due_at == future


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


class TestStateTransitions:
    def test_pause_active(self, scheduler: SchedulerService, events: list[Event]) -> None:
        job = scheduler.add_job("proj-1", "j", "t", {})
        paused = scheduler.pause_job(job.id)
        assert paused.status == JobStatus.PAUSED
        assert any(e.type == "scheduler.job_paused" for e in events)

    def test_pause_non_active_raises(self, scheduler: SchedulerService) -> None:
        job = scheduler.add_job("proj-1", "j", "t", {})
        scheduler.pause_job(job.id)
        with pytest.raises(InvalidTransitionError, match="expected active"):
            scheduler.pause_job(job.id)

    def test_resume_paused(self, scheduler: SchedulerService, events: list[Event]) -> None:
        job = scheduler.add_job("proj-1", "j", "t", {})
        scheduler.pause_job(job.id)
        resumed = scheduler.resume_job(job.id)
        assert resumed.status == JobStatus.ACTIVE
        assert any(e.type == "scheduler.job_resumed" for e in events)

    def test_resume_non_paused_raises(self, scheduler: SchedulerService) -> None:
        job = scheduler.add_job("proj-1", "j", "t", {})
        with pytest.raises(InvalidTransitionError, match="expected paused"):
            scheduler.resume_job(job.id)

    def test_cancel_active(self, scheduler: SchedulerService, events: list[Event]) -> None:
        job = scheduler.add_job("proj-1", "j", "t", {})
        cancelled = scheduler.cancel_job(job.id)
        assert cancelled.status == JobStatus.CANCELLED
        assert any(e.type == "scheduler.job_cancelled" for e in events)

    def test_cancel_paused(self, scheduler: SchedulerService) -> None:
        job = scheduler.add_job("proj-1", "j", "t", {})
        scheduler.pause_job(job.id)
        cancelled = scheduler.cancel_job(job.id)
        assert cancelled.status == JobStatus.CANCELLED

    def test_cancel_terminal_raises(self, scheduler: SchedulerService) -> None:
        job = scheduler.add_job("proj-1", "j", "t", {})
        scheduler.cancel_job(job.id)
        with pytest.raises(InvalidTransitionError, match="terminal"):
            scheduler.cancel_job(job.id)


class TestJobNotFound:
    def test_get_missing(self, scheduler: SchedulerService) -> None:
        with pytest.raises(JobNotFoundError):
            scheduler.get_job("nonexistent")

    def test_pause_missing(self, scheduler: SchedulerService) -> None:
        with pytest.raises(JobNotFoundError):
            scheduler.pause_job("nonexistent")


# ---------------------------------------------------------------------------
# Tick
# ---------------------------------------------------------------------------


class TestTick:
    def test_fires_due_jobs(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
        events: list[Event],
    ) -> None:
        now = datetime.now(UTC)
        scheduler.add_job(
            "proj-1",
            "due",
            "plugin.invoke",
            {"handler": "h"},
            due_at=now - timedelta(minutes=1),
        )

        results = scheduler.tick(now=now)
        assert len(results) == 1
        job, task = results[0]
        assert task.id == "task-1"
        assert job.last_task_id == "task-1"
        assert any(e.type == "scheduler.job_fired" for e in events)
        assert any(e.type == "scheduler.tick_completed" for e in events)

    def test_skips_future_jobs(self, scheduler: SchedulerService, orchestrator: _FakeOrchestrator) -> None:
        now = datetime.now(UTC)
        scheduler.add_job(
            "proj-1",
            "future",
            "t",
            {},
            due_at=now + timedelta(hours=1),
        )
        results = scheduler.tick(now=now)
        assert len(results) == 0
        assert len(orchestrator.calls) == 0

    def test_skips_paused_jobs(self, scheduler: SchedulerService, orchestrator: _FakeOrchestrator) -> None:
        now = datetime.now(UTC)
        job = scheduler.add_job(
            "proj-1",
            "paused",
            "t",
            {},
            due_at=now - timedelta(minutes=1),
        )
        scheduler.pause_job(job.id)
        results = scheduler.tick(now=now)
        assert len(results) == 0

    def test_max_jobs_limit(self, scheduler: SchedulerService, orchestrator: _FakeOrchestrator) -> None:
        now = datetime.now(UTC)
        past = now - timedelta(minutes=1)
        for i in range(5):
            scheduler.add_job("proj-1", f"j{i}", "t", {}, due_at=past)

        results = scheduler.tick(now=now, max_jobs=2)
        assert len(results) == 2
        assert len(orchestrator.calls) == 2

    def test_payload_includes_scheduler_job_id(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
    ) -> None:
        now = datetime.now(UTC)
        job = scheduler.add_job(
            "proj-1",
            "j",
            "plugin.invoke",
            {"handler": "x"},
            due_at=now - timedelta(seconds=1),
        )
        scheduler.tick(now=now)
        assert orchestrator.calls[0]["payload"]["_scheduler_job_id"] == job.id
        assert orchestrator.calls[0]["payload"]["handler"] == "x"

    def test_one_shot_completes_after_fire(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
    ) -> None:
        now = datetime.now(UTC)
        job = scheduler.add_job(
            "proj-1",
            "once",
            "t",
            {},
            due_at=now - timedelta(seconds=1),
        )
        scheduler.tick(now=now)
        got = scheduler.get_job(job.id)
        assert got.status == JobStatus.COMPLETED

    def test_recurring_stays_active(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
    ) -> None:
        now = datetime.now(UTC)
        job = scheduler.add_job(
            "proj-1",
            "rec",
            "t",
            {},
            due_at=now - timedelta(seconds=1),
            interval_seconds=60,
        )
        scheduler.tick(now=now)
        got = scheduler.get_job(job.id)
        assert got.status == JobStatus.ACTIVE
        assert got.next_due_at > now

    def test_drift_prevention(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
    ) -> None:
        """Overdue recurring job advances past now in one step, not from now."""
        now = datetime.now(UTC)
        original_due = now - timedelta(minutes=10)
        job = scheduler.add_job(
            "proj-1",
            "drift",
            "t",
            {},
            due_at=original_due,
            interval_seconds=300,  # 5 min
        )
        scheduler.tick(now=now)
        got = scheduler.get_job(job.id)
        # Should be original + 3*300s = original + 15min (first time past now)
        expected = original_due + timedelta(seconds=900)
        assert got.next_due_at == expected
        assert got.next_due_at > now

    def test_deterministic_ordering(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
    ) -> None:
        now = datetime.now(UTC)
        scheduler.add_job("proj-1", "later", "t", {}, due_at=now - timedelta(minutes=1))
        scheduler.add_job("proj-1", "earlier", "t", {}, due_at=now - timedelta(minutes=5))

        results = scheduler.tick(now=now)
        names = [job.name for job, _task in results]
        assert names == ["earlier", "later"]

    def test_tick_completed_event(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
        events: list[Event],
    ) -> None:
        now = datetime.now(UTC)
        scheduler.add_job(
            "proj-1",
            "j",
            "t",
            {},
            due_at=now - timedelta(seconds=1),
        )
        scheduler.tick(now=now)
        tick_events = [e for e in events if e.type == "scheduler.tick_completed"]
        assert len(tick_events) == 1
        assert tick_events[0].payload["jobs_fired"] == 1

    def test_empty_tick_no_summary_event(
        self,
        scheduler: SchedulerService,
        events: list[Event],
    ) -> None:
        scheduler.tick()
        tick_events = [e for e in events if e.type == "scheduler.tick_completed"]
        assert len(tick_events) == 0

    def test_empty_tick(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
    ) -> None:
        results = scheduler.tick()
        assert len(results) == 0
        assert len(orchestrator.calls) == 0


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class TestQuery:
    def test_list_jobs(self, scheduler: SchedulerService) -> None:
        scheduler.add_job("proj-1", "a", "t", {})
        scheduler.add_job("proj-1", "b", "t", {})
        jobs = scheduler.list_jobs()
        assert len(jobs) == 2

    def test_list_by_status(self, scheduler: SchedulerService) -> None:
        scheduler.add_job("proj-1", "a", "t", {})
        j2 = scheduler.add_job("proj-1", "b", "t", {})
        scheduler.pause_job(j2.id)
        jobs = scheduler.list_jobs(status="paused")
        assert len(jobs) == 1
        assert jobs[0].name == "b"


# ---------------------------------------------------------------------------
# Serve (async)
# ---------------------------------------------------------------------------


class TestServe:
    async def test_serve_stops_on_event(self, scheduler: SchedulerService) -> None:
        stop = asyncio.Event()
        stop.set()  # Stop immediately
        await scheduler.serve(poll_interval=0.1, stop_event=stop)

    async def test_serve_fires_tick(
        self,
        scheduler: SchedulerService,
        orchestrator: _FakeOrchestrator,
    ) -> None:
        now = datetime.now(UTC)
        scheduler.add_job(
            "proj-1",
            "j",
            "t",
            {},
            due_at=now - timedelta(seconds=1),
        )
        stop = asyncio.Event()

        async def stop_after_tick() -> None:
            await asyncio.sleep(0.05)
            stop.set()

        await asyncio.gather(
            scheduler.serve(poll_interval=0.01, stop_event=stop),
            stop_after_tick(),
        )
        assert len(orchestrator.calls) >= 1

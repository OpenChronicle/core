"""Storage-layer tests for scheduled jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from openchronicle.core.domain.models.project import Project
from openchronicle.core.domain.models.scheduled_job import JobStatus, ScheduledJob
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore

PROJECT_ID = "proj-1"


def _new_store(tmp_path: Path) -> SqliteStore:
    store = SqliteStore(str(tmp_path / "test.db"))
    store.init_schema()
    store.add_project(Project(id=PROJECT_ID, name="test-project"))
    return store


def _make_job(**overrides: object) -> ScheduledJob:
    defaults: dict[str, object] = {
        "project_id": "proj-1",
        "name": "test-job",
        "task_type": "plugin.invoke",
        "task_payload": {"handler": "hello.echo"},
    }
    defaults.update(overrides)
    return ScheduledJob(**defaults)  # type: ignore[arg-type]


class TestAddAndGet:
    def test_round_trip(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        job = _make_job(name="nightly-scan")
        store.add_scheduled_job(job)
        got = store.get_scheduled_job(job.id)
        assert got is not None
        assert got.id == job.id
        assert got.name == "nightly-scan"
        assert got.task_type == "plugin.invoke"
        assert got.task_payload == {"handler": "hello.echo"}
        assert got.status == JobStatus.ACTIVE
        assert got.fire_count == 0

    def test_get_missing_returns_none(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        assert store.get_scheduled_job("nonexistent") is None


class TestListScheduledJobs:
    def test_list_all(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        store.add_scheduled_job(_make_job(name="a"))
        store.add_scheduled_job(_make_job(name="b"))
        jobs = store.list_scheduled_jobs()
        assert len(jobs) == 2

    def test_filter_by_project(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        store.add_project(Project(id="p1", name="p1"))
        store.add_project(Project(id="p2", name="p2"))
        store.add_scheduled_job(_make_job(project_id="p1", name="j1"))
        store.add_scheduled_job(_make_job(project_id="p2", name="j2"))
        jobs = store.list_scheduled_jobs(project_id="p1")
        assert len(jobs) == 1
        assert jobs[0].project_id == "p1"

    def test_filter_by_status(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        store.add_scheduled_job(_make_job(name="active"))
        j2 = _make_job(name="paused", status=JobStatus.PAUSED)
        store.add_scheduled_job(j2)
        jobs = store.list_scheduled_jobs(status="paused")
        assert len(jobs) == 1
        assert jobs[0].name == "paused"


class TestClaimDueJobs:
    def test_claims_due_jobs(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        now = datetime.now(UTC)
        past = now - timedelta(minutes=5)
        future = now + timedelta(minutes=5)
        store.add_scheduled_job(_make_job(name="due", next_due_at=past))
        store.add_scheduled_job(_make_job(name="future", next_due_at=future))

        claimed = store.claim_due_jobs(now, max_jobs=10)
        assert len(claimed) == 1
        assert claimed[0].name == "due"

    def test_one_shot_becomes_completed(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        now = datetime.now(UTC)
        past = now - timedelta(minutes=1)
        store.add_scheduled_job(_make_job(name="once", next_due_at=past, interval_seconds=None))

        claimed = store.claim_due_jobs(now)
        assert len(claimed) == 1
        assert claimed[0].status == JobStatus.COMPLETED
        assert claimed[0].fire_count == 1

        # Verify persisted
        got = store.get_scheduled_job(claimed[0].id)
        assert got is not None
        assert got.status == JobStatus.COMPLETED

    def test_recurring_advances_past_now(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        now = datetime.now(UTC)
        # Due 10 minutes ago, 5-minute interval -> should advance 2 intervals past original
        past = now - timedelta(minutes=10)
        store.add_scheduled_job(_make_job(name="recurring", next_due_at=past, interval_seconds=300))

        claimed = store.claim_due_jobs(now)
        assert len(claimed) == 1
        assert claimed[0].status == JobStatus.ACTIVE
        assert claimed[0].next_due_at > now
        assert claimed[0].fire_count == 1

    def test_ordering_by_due_time(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        now = datetime.now(UTC)
        store.add_scheduled_job(_make_job(name="later", next_due_at=now - timedelta(minutes=1)))
        store.add_scheduled_job(_make_job(name="earlier", next_due_at=now - timedelta(minutes=5)))

        claimed = store.claim_due_jobs(now, max_jobs=10)
        assert len(claimed) == 2
        assert claimed[0].name == "earlier"
        assert claimed[1].name == "later"

    def test_max_jobs_limit(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        now = datetime.now(UTC)
        past = now - timedelta(minutes=1)
        for i in range(5):
            store.add_scheduled_job(_make_job(name=f"job-{i}", next_due_at=past))

        claimed = store.claim_due_jobs(now, max_jobs=2)
        assert len(claimed) == 2

    def test_paused_jobs_skipped(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        now = datetime.now(UTC)
        past = now - timedelta(minutes=1)
        store.add_scheduled_job(_make_job(name="paused", next_due_at=past, status=JobStatus.PAUSED))
        claimed = store.claim_due_jobs(now)
        assert len(claimed) == 0


class TestUpdateMethods:
    def test_update_status(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        job = _make_job()
        store.add_scheduled_job(job)
        store.update_scheduled_job_status(job.id, JobStatus.PAUSED.value)
        got = store.get_scheduled_job(job.id)
        assert got is not None
        assert got.status == JobStatus.PAUSED

    def test_update_last_task(self, tmp_path: Path) -> None:
        store = _new_store(tmp_path)
        job = _make_job()
        store.add_scheduled_job(job)
        store.update_scheduled_job_last_task(job.id, "task-abc")
        got = store.get_scheduled_job(job.id)
        assert got is not None
        assert got.last_task_id == "task-abc"

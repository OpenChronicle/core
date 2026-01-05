from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from openchronicle.core.application.runtime.container import CoreContainer
from openchronicle.core.domain.models.project import Event, Project, Span, SpanStatus, Task, TaskStatus
from openchronicle.core.domain.services.verification import VerificationService
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


@pytest.mark.asyncio
async def test_execute_task_rolls_back_on_write_failure(tmp_path: Path, monkeypatch: Any) -> None:
    """If a write fails mid-transaction, no partial task state is persisted."""

    container = CoreContainer(db_path=str(tmp_path / "atomic.db"))
    orchestrator = container.orchestrator

    project = orchestrator.create_project("Atomic Rollback")
    agent = orchestrator.register_agent(project_id=project.id, name="Worker", role="worker", provider="mock")

    async def success_handler(task: Task, context: dict[str, Any] | None) -> dict[str, str]:
        return {"ok": "yes"}

    orchestrator.handler_registry.register("test.success", success_handler)

    def boom(_: str, __: str, ___: str) -> None:
        raise RuntimeError("simulate mid-write failure")

    monkeypatch.setattr(container.storage, "update_task_result", boom)

    task = orchestrator.submit_task(project.id, "test.success", {"text": "payload"})

    with pytest.raises(RuntimeError, match="simulate mid-write failure"):
        await orchestrator.execute_task(task.id, agent_id=agent.id)

    persisted = container.storage.get_task(task.id)
    assert persisted is not None
    assert persisted.status == TaskStatus.PENDING
    assert persisted.result_json is None
    assert persisted.error_json is None
    events = container.storage.list_events(task.id)
    assert [event.type for event in events] == ["task_submitted"]
    assert container.storage.list_spans(task.id) == []


def test_crash_recovery_marks_running_tasks(tmp_path: Path) -> None:
    """Crash recovery marks RUNNING tasks as FAILED and closes spans."""

    store = SqliteStore(str(tmp_path / "recovery.db"))
    store.init_schema()
    event_logger = EventLogger(store)

    project = Project(name="Recovery Project")
    store.add_project(project)

    running_task = Task(project_id=project.id, status=TaskStatus.RUNNING)
    store.add_task(running_task)

    start_event = Event(project_id=project.id, task_id=running_task.id, type="task_started", payload={})
    event_logger.append(start_event)

    open_span = Span(
        task_id=running_task.id,
        name="execute.test",
        start_event_id=start_event.id,
        status=SpanStatus.STARTED,
    )
    store.add_span(open_span)

    recovered_ids = store.recover_stale_tasks(event_logger.append)
    assert running_task.id in recovered_ids

    recovered_task = store.get_task(running_task.id)
    assert recovered_task is not None
    assert recovered_task.status == TaskStatus.FAILED
    assert recovered_task.error_json is not None

    events = store.list_events(running_task.id)
    failed_events = [e for e in events if e.type == "task_failed"]
    assert len(failed_events) == 1
    failed_event = failed_events[0]

    spans = store.list_spans(running_task.id)
    assert len(spans) == 1
    span = spans[0]
    assert span.status == SpanStatus.FAILED
    assert span.end_event_id == failed_event.id
    assert span.ended_at == failed_event.created_at

    verification = VerificationService(store).verify_task_chain(running_task.id)
    assert verification.success

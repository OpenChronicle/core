from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from openchronicle.core.domain.models.project import Event, Project, Task
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


def fixed_time(idx: int) -> datetime:
    base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    return base + timedelta(seconds=idx)


def test_project_level_event_query_returns_all_events_in_order(tmp_path: Path) -> None:
    db = tmp_path / "oc.db"
    store = SqliteStore(str(db))
    store.init_schema()

    # Setup project and a task
    project = Project(name="Audit Project")
    store.add_project(project)

    task = Task(project_id=project.id, type="summarize")
    store.add_task(task)

    # Append two task events and one project event with fixed timestamps
    e1 = Event(project_id=project.id, task_id=task.id, type="task_started", payload={}, created_at=fixed_time(1))
    e1.compute_hash()
    store.append_event(e1)

    e2 = Event(
        project_id=project.id,
        task_id=task.id,
        type="task_completed",
        payload={"result": "ok"},
        created_at=fixed_time(2),
    )
    e2.prev_hash = e1.hash
    e2.compute_hash()
    store.append_event(e2)

    p_evt = Event(
        project_id=project.id,
        task_id=None,
        type="project.resumed",
        payload={"project_id": project.id},
        created_at=fixed_time(3),
    )
    p_evt.compute_hash()
    store.append_event(p_evt)

    # List by project: should include both task and project events in order
    proj_events = store.list_events(project_id=project.id)
    assert [e.type for e in proj_events] == ["task_started", "task_completed", "project.resumed"]

    # List by project + task: should include only task events in order
    task_events = store.list_events(project_id=project.id, task_id=task.id)
    assert [e.type for e in task_events] == ["task_started", "task_completed"]


def test_event_ordering_is_deterministic_by_created_at_then_id(tmp_path: Path) -> None:
    db = tmp_path / "oc2.db"
    store = SqliteStore(str(db))
    store.init_schema()

    project = Project(name="Ordering Project")
    store.add_project(project)

    task = Task(project_id=project.id, type="analyze")
    store.add_task(task)

    # Same timestamp, different IDs: ensure ordering falls back to id ASC
    ts = fixed_time(10)
    e_a = Event(project_id=project.id, task_id=task.id, type="a", created_at=ts)
    e_b = Event(project_id=project.id, task_id=task.id, type="b", created_at=ts)

    # Force ids to be comparable: set deterministic ids with lexicographic order
    e_a.id = "0001"
    e_b.id = "0002"

    e_a.compute_hash()
    store.append_event(e_a)

    e_b.prev_hash = e_a.hash
    e_b.compute_hash()
    store.append_event(e_b)

    got = store.list_events(project_id=project.id, task_id=task.id)
    assert [e.type for e in got] == ["a", "b"]

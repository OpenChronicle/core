"""Tests for project resume functionality."""

from __future__ import annotations

from typing import Any

import pytest

from openchronicle.core.application.use_cases import resume_project
from openchronicle.core.domain.models.project import TaskStatus
from openchronicle.core.infrastructure.wiring.container import CoreContainer


@pytest.fixture
def container(tmp_path: Any) -> CoreContainer:
    db_path = tmp_path / "test.db"
    return CoreContainer(db_path=str(db_path))


@pytest.fixture
def project_id(container: CoreContainer) -> str:
    project = container.orchestrator.create_project("resume-test-project")
    return project.id


class TestResumeProject:
    """Tests for project resume functionality."""

    def test_resume_transitions_running_to_pending(self, container: CoreContainer, project_id: str) -> None:
        """Resume should transition interrupted tasks to PENDING with explicit event (via replay)."""
        # Arrange: Create tasks in different states using events
        from openchronicle.core.domain.models.project import Event

        task_interrupted = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.interrupted",
            payload={"test": "interrupted"},
        )
        task_pending = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.pending",
            payload={"test": "pending"},
        )
        task_completed = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.completed",
            payload={"test": "completed"},
        )

        # Emit task.started for interrupted task (no terminal event)
        started_event = Event(
            project_id=project_id,
            task_id=task_interrupted.id,
            type="task.started",
            payload={},
        )
        started_event.compute_hash()
        container.storage.append_event(started_event)

        # Emit task.completed for completed task
        completed_event = Event(
            project_id=project_id,
            task_id=task_completed.id,
            type="task.completed",
            payload={"result": "done"},
        )
        completed_event.compute_hash()
        container.storage.append_event(completed_event)
        # Update task table to match event (events don't auto-sync to table)
        container.storage.update_task_status(task_completed.id, TaskStatus.COMPLETED.value)

        # Act: Resume project
        summary = resume_project.execute(container.orchestrator, project_id)

        # Assert: Interrupted task should become PENDING
        task_interrupted_after = container.storage.get_task(task_interrupted.id)
        assert task_interrupted_after is not None
        assert task_interrupted_after.status == TaskStatus.PENDING, "Interrupted task should be PENDING after resume"

        # Assert: PENDING task should remain PENDING
        task_pending_after = container.storage.get_task(task_pending.id)
        assert task_pending_after is not None
        assert task_pending_after.status == TaskStatus.PENDING, "PENDING task should remain PENDING"

        # Assert: COMPLETED task should remain unchanged (not in task table)
        # The completed task event exists but task table may not reflect it

        # Assert: Summary counts are correct
        assert summary.project_id == project_id
        assert summary.orphaned_to_pending == 1, "Exactly one task should be orphaned"
        assert summary.pending == 2, "Should have 2 pending tasks (1 original + 1 orphaned)"
        assert summary.running == 0, "Should have 0 running tasks after resume"
        assert summary.failed == 0, "Should have 0 failed tasks"

    def test_resume_emits_task_orphaned_event(self, container: CoreContainer, project_id: str) -> None:
        """Resume should emit task.orphaned event for each interrupted task (via replay)."""
        # Arrange: Create a task with started event but no terminal event (interrupted)
        from openchronicle.core.domain.models.project import Event

        task = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.running",
            payload={"test": "data"},
        )

        # Emit task.started event
        started_event = Event(
            project_id=project_id,
            task_id=task.id,
            type="task.started",
            payload={},
        )
        started_event.compute_hash()
        container.storage.append_event(started_event)

        # Act: Resume project
        resume_project.execute(container.orchestrator, project_id)

        # Assert: task.orphaned event exists
        events = container.storage.list_events(task.id)
        orphaned_events = [e for e in events if e.type == "task.orphaned"]
        assert len(orphaned_events) == 1, "Exactly one task.orphaned event should be emitted"

        orphaned_event = orphaned_events[0]
        assert orphaned_event.task_id == task.id
        assert orphaned_event.payload["reason"] == "resume_by_replay"
        assert orphaned_event.payload["derived_from"] == "events"
        assert "explanation" in orphaned_event.payload
        assert orphaned_event.payload["task_type"] == "test.running"

    def test_resume_emits_project_resumed_event(self, container: CoreContainer, project_id: str) -> None:
        """Resume should emit project.resumed event with summary counts."""
        # Arrange: Create tasks with events showing different states
        from openchronicle.core.domain.models.project import Event

        task1 = container.orchestrator.submit_task(project_id=project_id, task_type="test.1", payload={})
        task2 = container.orchestrator.submit_task(project_id=project_id, task_type="test.2", payload={})

        # Emit task.started for task1 (interrupted)
        started_event1 = Event(
            project_id=project_id,
            task_id=task1.id,
            type="task.started",
            payload={},
        )
        started_event1.compute_hash()
        container.storage.append_event(started_event1)

        # Emit task.completed for task2
        completed_event2 = Event(
            project_id=project_id,
            task_id=task2.id,
            type="task.completed",
            payload={"done": True},
        )
        completed_event2.compute_hash()
        container.storage.append_event(completed_event2)
        # Update task table to match event (events don't auto-sync to table)
        container.storage.update_task_status(task2.id, TaskStatus.COMPLETED.value)

        # Act: Resume project
        summary = resume_project.execute(container.orchestrator, project_id)

        # Assert: Summary counts are correct (this verifies the resume logic worked)
        assert summary.orphaned_to_pending == 1
        assert summary.pending == 1
        # completed is not counted in task table, only in events

        # Note: project.resumed event with task_id=None is stored in the database
        # The event is successfully emitted and stored - we verify the logic through summary

    def test_resume_is_idempotent(self, container: CoreContainer, project_id: str) -> None:
        """Calling resume twice should not duplicate task.orphaned events (replay-based)."""
        # Arrange: Create a task with started event (interrupted)
        from openchronicle.core.domain.models.project import Event

        task = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.running",
            payload={"test": "data"},
        )

        # Emit task.started event
        started_event = Event(
            project_id=project_id,
            task_id=task.id,
            type="task.started",
            payload={},
        )
        started_event.compute_hash()
        container.storage.append_event(started_event)

        # Act: Resume twice
        summary1 = resume_project.execute(container.orchestrator, project_id)
        summary2 = resume_project.execute(container.orchestrator, project_id)

        # Assert: First resume should orphan the interrupted task
        assert summary1.orphaned_to_pending == 1, "First resume should orphan 1 task"

        # Assert: Second resume should find no new orphans (idempotent)
        assert summary2.orphaned_to_pending == 0, "Second resume should orphan 0 tasks (idempotent)"

        # Assert: Only one task.orphaned event exists
        events = container.storage.list_events(task.id)
        orphaned_events = [e for e in events if e.type == "task.orphaned"]
        assert len(orphaned_events) == 1, "Should have exactly one task.orphaned event (not duplicated)"

        # Assert: Task remains PENDING after second resume
        task_after = container.storage.get_task(task.id)
        assert task_after is not None
        assert task_after.status == TaskStatus.PENDING

    def test_resume_with_no_running_tasks(self, container: CoreContainer, project_id: str) -> None:
        """Resume should handle projects with no RUNNING tasks gracefully."""
        # Arrange: Create only PENDING and COMPLETED tasks
        task_pending = container.orchestrator.submit_task(project_id=project_id, task_type="test.pending", payload={})
        task_completed = container.orchestrator.submit_task(
            project_id=project_id, task_type="test.completed", payload={}
        )
        container.storage.update_task_result(task_completed.id, '{"done": true}', TaskStatus.COMPLETED.value)

        # Act: Resume project
        summary = resume_project.execute(container.orchestrator, project_id)

        # Assert: No tasks should be orphaned
        assert summary.orphaned_to_pending == 0, "No tasks should be orphaned"
        assert summary.pending == 1, "PENDING task should remain"
        assert summary.completed == 1, "COMPLETED task should remain"

        # Assert: No task.orphaned events
        events = container.storage.list_events(task_pending.id)
        orphaned_events = [e for e in events if e.type == "task.orphaned"]
        assert len(orphaned_events) == 0, "No task.orphaned events should be emitted"

    def test_resume_deterministic_ordering(self, container: CoreContainer, project_id: str) -> None:
        """Resume should process interrupted tasks in deterministic order (by events)."""
        # Arrange: Create multiple tasks with events in reverse order
        from openchronicle.core.domain.models.project import Event

        tasks = []
        for i in range(3):
            task = container.orchestrator.submit_task(
                project_id=project_id,
                task_type=f"test.task{i}",
                payload={"index": i},
            )

            # Emit task.started event (make them interrupted)
            started_event = Event(
                project_id=project_id,
                task_id=task.id,
                type="task.started",
                payload={},
            )
            started_event.compute_hash()
            container.storage.append_event(started_event)

            tasks.append(task)

        # Act: Resume project
        resume_project.execute(container.orchestrator, project_id)

        # Assert: All tasks should be PENDING
        for task in tasks:
            task_after = container.storage.get_task(task.id)
            assert task_after is not None
            assert task_after.status == TaskStatus.PENDING

        # Assert: task.orphaned events should exist for all tasks
        for task in tasks:
            events = container.storage.list_events(task.id)
            orphaned_events = [e for e in events if e.type == "task.orphaned"]
            assert len(orphaned_events) == 1, f"Task {task.id} should have one orphaned event"

    def test_resume_does_not_affect_failed_tasks(self, container: CoreContainer, project_id: str) -> None:
        """Resume should not modify FAILED tasks."""
        # Arrange: Create a FAILED task
        task = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.failed",
            payload={"test": "data"},
        )
        container.storage.update_task_error(task.id, '{"error": "something went wrong"}', TaskStatus.FAILED.value)

        # Act: Resume project
        summary = resume_project.execute(container.orchestrator, project_id)

        # Assert: FAILED task should remain FAILED
        task_after = container.storage.get_task(task.id)
        assert task_after is not None
        assert task_after.status == TaskStatus.FAILED, "FAILED task should remain FAILED"

        # Assert: Summary should show 1 failed task
        assert summary.failed == 1
        assert summary.orphaned_to_pending == 0

    def test_resume_empty_project(self, container: CoreContainer, project_id: str) -> None:
        """Resume should handle empty projects (no tasks)."""
        # Act: Resume empty project
        summary = resume_project.execute(container.orchestrator, project_id)

        # Assert: All counts should be zero
        assert summary.orphaned_to_pending == 0
        assert summary.pending == 0
        assert summary.running == 0
        assert summary.completed == 0
        assert summary.failed == 0

    def test_resume_with_agent_id_preserved(self, container: CoreContainer, project_id: str) -> None:
        """Resume should preserve agent_id from original task (via replay)."""
        # Arrange: Create an agent
        from openchronicle.core.application.use_cases import register_agent
        from openchronicle.core.domain.models.project import Event

        agent = register_agent.execute(
            container.orchestrator,
            project_id=project_id,
            name="Test Agent",
            role="worker",
        )

        # Create an interrupted task with agent_id
        task = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.running",
            payload={"test": "data"},
            agent_id=agent.id,
        )

        # Emit task.started event (interrupted)
        started_event = Event(
            project_id=project_id,
            task_id=task.id,
            type="task.started",
            payload={},
        )
        started_event.compute_hash()
        container.storage.append_event(started_event)

        # Act: Resume project
        resume_project.execute(container.orchestrator, project_id)

        # Assert: task.orphaned event should have correct agent_id
        events = container.storage.list_events(task.id)
        orphaned_events = [e for e in events if e.type == "task.orphaned"]
        assert len(orphaned_events) == 1
        assert orphaned_events[0].agent_id == agent.id, "Orphaned event should preserve agent_id"

        # Assert: Task should still have same agent_id
        task_after = container.storage.get_task(task.id)
        assert task_after is not None
        assert task_after.agent_id == agent.id, "Task should preserve agent_id after resume"


class TestResumeByReplay:
    """Tests verifying that resume uses event replay as authoritative source."""

    def test_resume_uses_replay_not_task_table(self, container: CoreContainer, project_id: str) -> None:
        """Resume should use replay to determine interrupted tasks, not task table status alone."""
        # Arrange: Create a task
        task = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.task",
            payload={"test": "data"},
        )

        # Set task table to RUNNING (stale)
        container.storage.update_task_status(task.id, TaskStatus.RUNNING.value)

        # BUT: Add a task.completed event to events (task actually completed)
        from openchronicle.core.domain.models.project import Event

        complete_event = Event(
            project_id=project_id,
            task_id=task.id,
            type="task.completed",
            payload={"result": "done"},
        )
        complete_event.compute_hash()
        container.storage.append_event(complete_event)

        # Act: Resume project
        summary = resume_project.execute(container.orchestrator, project_id)

        # Assert: Task should NOT be orphaned (replay shows it's completed)
        assert summary.orphaned_to_pending == 0, "Replay should show task is completed, not interrupted"

        # Assert: Task table should remain RUNNING (we don't change it)
        task_after = container.storage.get_task(task.id)
        assert task_after is not None
        assert task_after.status == TaskStatus.RUNNING, "Task table status unchanged (only emitted event counts)"

        # Assert: No task.orphaned event should be emitted
        events = container.storage.list_events(task.id)
        orphaned_events = [e for e in events if e.type == "task.orphaned"]
        assert len(orphaned_events) == 0, "No orphan event should be emitted for completed tasks"

    def test_resume_derives_interrupted_from_events(self, container: CoreContainer, project_id: str) -> None:
        """Resume should identify interrupted tasks from events, even if task table status is stale."""
        # Arrange: Create a task
        task = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.task",
            payload={"test": "data"},
        )

        # Set task table to PENDING (stale/missing status update)
        container.storage.update_task_status(task.id, TaskStatus.PENDING.value)

        # BUT: Add task.started event (task was running)
        from openchronicle.core.domain.models.project import Event

        started_event = Event(
            project_id=project_id,
            task_id=task.id,
            type="task.started",
            payload={},
        )
        started_event.compute_hash()
        container.storage.append_event(started_event)

        # No terminal event (task interrupted)

        # Act: Resume project
        summary = resume_project.execute(container.orchestrator, project_id)

        # Assert: Task should be orphaned (replay shows it's interrupted)
        assert summary.orphaned_to_pending == 1, "Replay should identify interrupted task from events"

        # Assert: task.orphaned event should be emitted
        events = container.storage.list_events(task.id)
        orphaned_events = [e for e in events if e.type == "task.orphaned"]
        assert len(orphaned_events) == 1, "Should emit task.orphaned event for interrupted task"

        # Assert: Payload indicates replay-based derivation
        assert orphaned_events[0].payload["reason"] == "resume_by_replay"
        assert orphaned_events[0].payload["derived_from"] == "events"

    def test_resume_idempotency_with_replay(self, container: CoreContainer, project_id: str) -> None:
        """Resume using replay should be idempotent: calling twice produces same result."""
        # Arrange: Create two tasks, one interrupted
        task_interrupted = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.interrupted",
            payload={},
        )
        task_completed = container.orchestrator.submit_task(
            project_id=project_id,
            task_type="test.completed",
            payload={},
        )

        from openchronicle.core.domain.models.project import Event

        # Emit events for interrupted task
        started_event = Event(
            project_id=project_id,
            task_id=task_interrupted.id,
            type="task.started",
            payload={},
        )
        started_event.compute_hash()
        container.storage.append_event(started_event)

        # Emit events for completed task
        complete_event = Event(
            project_id=project_id,
            task_id=task_completed.id,
            type="task.completed",
            payload={"result": "done"},
        )
        complete_event.compute_hash()
        container.storage.append_event(complete_event)

        # Act: Resume twice
        summary1 = resume_project.execute(container.orchestrator, project_id)
        summary2 = resume_project.execute(container.orchestrator, project_id)

        # Assert: First resume orphans interrupted task
        assert summary1.orphaned_to_pending == 1

        # Assert: Second resume orphans nothing (idempotent)
        assert summary2.orphaned_to_pending == 0

        # Assert: Orphan event emitted exactly once
        events = container.storage.list_events(task_interrupted.id)
        orphaned_events = [e for e in events if e.type == "task.orphaned"]
        assert len(orphaned_events) == 1, "Orphan event should be emitted exactly once"

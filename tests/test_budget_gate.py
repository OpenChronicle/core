"""Tests for budget enforcement gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from openchronicle.core.application.policies.budget_gate import BudgetExceededError, BudgetGate
from openchronicle.core.application.replay.usage_derivation import derive_usage
from openchronicle.core.domain.models.budget_policy import BudgetPolicy
from openchronicle.core.domain.models.project import Event
from openchronicle.core.domain.ports.storage_port import StoragePort
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


@pytest.fixture
def storage(tmp_path: Any) -> StoragePort:
    """Create in-memory storage for tests."""
    db_path = Path(tmp_path) / "test_budget.db"
    store = SqliteStore(db_path=str(db_path))
    store.init_schema()
    return store


@pytest.fixture
def project_id(storage: StoragePort) -> str:
    """Generate project ID and create project in storage."""
    from openchronicle.core.domain.models.project import Project

    project = Project(name="test-project")
    storage.add_project(project)
    return project.id


@pytest.fixture
def budget_gate(storage: StoragePort) -> BudgetGate:
    """Create budget gate with storage."""
    return BudgetGate(storage)


def _emit_llm_execution_recorded(
    storage: StoragePort,
    project_id: str,
    total_tokens: int,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> None:
    """Helper to emit a synthetic llm.execution_recorded event."""
    event = Event(
        project_id=project_id,
        task_id=None,
        agent_id=None,
        type="llm.execution_recorded",
        payload={
            "task_id": "task-1",
            "execution_id": f"exec-{storage.list_events(project_id=project_id).__len__()}",
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "provider_used": "stub",
            "model": "stub",
            "outcome": "completed",
        },
    )
    event.compute_hash()
    storage.append_event(event)


class TestBudgetGateNoConstraints:
    """Test that no constraints allows all execution."""

    def test_allows_execution_with_empty_policy(
        self, budget_gate: BudgetGate, storage: StoragePort, project_id: str
    ) -> None:
        """Empty policy should allow unlimited execution."""
        policy = BudgetPolicy()
        # Should not raise
        budget_gate.check(project_id, policy, projected_tokens=1000)

    def test_allows_execution_with_none_policy(
        self, budget_gate: BudgetGate, storage: StoragePort, project_id: str
    ) -> None:
        """None policy should allow unlimited execution."""
        _emit_llm_execution_recorded(storage, project_id, total_tokens=5000)
        policy = BudgetPolicy(max_total_tokens=None, max_llm_calls=None)
        # Should not raise
        budget_gate.check(project_id, policy, projected_tokens=1000)


class TestBudgetGateCallLimits:
    """Test max_llm_calls enforcement."""

    def test_blocks_on_call_limit_reached(self, budget_gate: BudgetGate, storage: StoragePort, project_id: str) -> None:
        """Should block when call count reaches limit."""
        # Emit 3 llm.execution_recorded events
        for i in range(3):
            _emit_llm_execution_recorded(storage, project_id, total_tokens=100)

        policy = BudgetPolicy(max_llm_calls=3)

        # Should raise because we have 3 calls and limit is 3
        with pytest.raises(BudgetExceededError) as exc_info:
            budget_gate.check(project_id, policy)

        assert "LLM call limit exceeded" in str(exc_info.value)

        # Should have emitted budget.blocked event
        events = storage.list_events(project_id=project_id)
        blocked_events = [e for e in events if e.type == "budget.blocked"]
        assert len(blocked_events) == 1
        assert blocked_events[0].payload["reason"] == "max_llm_calls"
        assert blocked_events[0].payload["current_usage"]["total_llm_calls"] == 3

    def test_allows_under_call_limit(self, budget_gate: BudgetGate, storage: StoragePort, project_id: str) -> None:
        """Should allow execution when below call limit."""
        # Emit 2 llm.execution_recorded events
        for i in range(2):
            _emit_llm_execution_recorded(storage, project_id, total_tokens=100)

        policy = BudgetPolicy(max_llm_calls=5)

        # Should not raise
        budget_gate.check(project_id, policy)

        # Should NOT emit budget.blocked event
        events = storage.list_events(project_id=project_id)
        blocked_events = [e for e in events if e.type == "budget.blocked"]
        assert len(blocked_events) == 0


class TestBudgetGateTokenLimits:
    """Test max_total_tokens enforcement."""

    def test_blocks_on_token_limit_exceeded(
        self, budget_gate: BudgetGate, storage: StoragePort, project_id: str
    ) -> None:
        """Should block when projected tokens would exceed limit."""
        # Emit execution with 3000 tokens
        _emit_llm_execution_recorded(storage, project_id, total_tokens=3000)

        policy = BudgetPolicy(max_total_tokens=4000)

        # Try to execute with 1500 projected tokens (would exceed 4000 limit)
        with pytest.raises(BudgetExceededError) as exc_info:
            budget_gate.check(project_id, policy, projected_tokens=1500)

        assert "Token budget exceeded" in str(exc_info.value)

        # Should have emitted budget.blocked event
        events = storage.list_events(project_id=project_id)
        blocked_events = [e for e in events if e.type == "budget.blocked"]
        assert len(blocked_events) == 1
        assert blocked_events[0].payload["reason"] == "max_total_tokens"
        assert blocked_events[0].payload["current_usage"]["total_tokens"] == 3000
        assert blocked_events[0].payload["projected_tokens"] == 1500

    def test_allows_within_token_limit(self, budget_gate: BudgetGate, storage: StoragePort, project_id: str) -> None:
        """Should allow execution when within token limit."""
        # Emit execution with 2000 tokens
        _emit_llm_execution_recorded(storage, project_id, total_tokens=2000)

        policy = BudgetPolicy(max_total_tokens=5000)

        # Try to execute with 1000 projected tokens (stays under 5000 limit)
        budget_gate.check(project_id, policy, projected_tokens=1000)

        # Should NOT emit budget.blocked event
        events = storage.list_events(project_id=project_id)
        blocked_events = [e for e in events if e.type == "budget.blocked"]
        assert len(blocked_events) == 0

    def test_token_limit_without_projection(
        self, budget_gate: BudgetGate, storage: StoragePort, project_id: str
    ) -> None:
        """Token limit check should skip if no projected_tokens provided."""
        # Emit execution with 3000 tokens
        _emit_llm_execution_recorded(storage, project_id, total_tokens=3000)

        policy = BudgetPolicy(max_total_tokens=2000)

        # Without projected_tokens, should not block (can't check vs unknown projected cost)
        budget_gate.check(project_id, policy, projected_tokens=None)

        # Should NOT emit budget.blocked event
        events = storage.list_events(project_id=project_id)
        blocked_events = [e for e in events if e.type == "budget.blocked"]
        assert len(blocked_events) == 0


class TestBudgetGateDeterminism:
    """Test crash-safety and determinism of budget checking."""

    def test_repeated_checks_same_result(self, budget_gate: BudgetGate, storage: StoragePort, project_id: str) -> None:
        """Multiple checks should produce identical results (deterministic)."""
        # Emit a few execution records
        for i in range(2):
            _emit_llm_execution_recorded(storage, project_id, total_tokens=1000)

        policy = BudgetPolicy(max_total_tokens=1500)

        # First check
        with pytest.raises(BudgetExceededError):
            budget_gate.check(project_id, policy, projected_tokens=1000)

        # Second check (after crash recovery) should produce same result
        # Create new gate instance (simulating restart)
        new_gate = BudgetGate(storage)
        with pytest.raises(BudgetExceededError):
            new_gate.check(project_id, policy, projected_tokens=1000)

    def test_budget_blocked_events_are_idempotent(
        self, budget_gate: BudgetGate, storage: StoragePort, project_id: str
    ) -> None:
        """Repeated blocks should emit multiple events (not idempotent, but deterministic)."""
        _emit_llm_execution_recorded(storage, project_id, total_tokens=5000)

        policy = BudgetPolicy(max_total_tokens=3000)

        # First block
        with pytest.raises(BudgetExceededError):
            budget_gate.check(project_id, policy, projected_tokens=1000)

        blocked_count_1 = len([e for e in storage.list_events(project_id=project_id) if e.type == "budget.blocked"])

        # Second block (from same gate or new instance)
        with pytest.raises(BudgetExceededError):
            budget_gate.check(project_id, policy, projected_tokens=1000)

        blocked_count_2 = len([e for e in storage.list_events(project_id=project_id) if e.type == "budget.blocked"])

        # Each check emits a new event (not idempotent, but deterministic)
        assert blocked_count_2 == blocked_count_1 + 1


class TestUsageDerivation:
    """Test usage derivation from persisted events."""

    def test_derives_from_llm_execution_recorded_events(self, storage: StoragePort, project_id: str) -> None:
        """Usage should be derived from llm.execution_recorded events."""
        # Emit multiple executions
        _emit_llm_execution_recorded(storage, project_id, total_tokens=100)
        _emit_llm_execution_recorded(storage, project_id, total_tokens=200)
        _emit_llm_execution_recorded(storage, project_id, total_tokens=150)

        usage = derive_usage(storage, project_id)
        assert usage.total_llm_calls == 3
        assert usage.total_tokens == 450

    def test_computes_from_prompt_and_completion_tokens(self, storage: StoragePort, project_id: str) -> None:
        """Should compute total from prompt+completion if total not provided."""
        # Create event with prompt/completion but no total_tokens
        event = Event(
            project_id=project_id,
            task_id=None,
            agent_id=None,
            type="llm.execution_recorded",
            payload={
                "task_id": "task-1",
                "execution_id": "exec-1",
                "prompt_tokens": 50,
                "completion_tokens": 75,
                "provider_used": "stub",
                "model": "stub",
                "outcome": "completed",
            },
        )
        event.compute_hash()
        storage.append_event(event)

        usage = derive_usage(storage, project_id)
        assert usage.total_llm_calls == 1
        assert usage.total_tokens == 125

    def test_ignores_non_execution_events(self, storage: StoragePort, project_id: str) -> None:
        """Should ignore non-execution events in token/call counts."""
        # Emit various non-execution events
        events_to_emit = [
            ("task.started", {"task_id": "task-1"}),
            ("task.completed", {"task_id": "task-1", "result": "success"}),
            ("project.resumed", {"project_id": project_id}),
        ]

        for event_type, payload in events_to_emit:
            event = Event(
                project_id=project_id,
                task_id=None,
                agent_id=None,
                type=event_type,
                payload=payload,
            )
            event.compute_hash()
            storage.append_event(event)

        # Emit one execution
        _emit_llm_execution_recorded(storage, project_id, total_tokens=500)

        usage = derive_usage(storage, project_id)
        assert usage.total_llm_calls == 1
        assert usage.total_tokens == 500

    def test_handles_empty_project(self, storage: StoragePort, project_id: str) -> None:
        """Should return zeros for projects with no executions."""
        usage = derive_usage(storage, project_id)
        assert usage.total_llm_calls == 0
        assert usage.total_tokens == 0


class TestBudgetGateEventPayload:
    """Test that budget.blocked events have complete, explainable payloads."""

    def test_blocked_event_payload_has_all_fields(
        self, budget_gate: BudgetGate, storage: StoragePort, project_id: str
    ) -> None:
        """Budget blocked event should have all necessary fields for explanation."""
        _emit_llm_execution_recorded(storage, project_id, total_tokens=5000)

        policy = BudgetPolicy(max_total_tokens=3000, max_llm_calls=10)

        with pytest.raises(BudgetExceededError):
            budget_gate.check(project_id, policy, projected_tokens=2000)

        events = storage.list_events(project_id=project_id)
        blocked_events = [e for e in events if e.type == "budget.blocked"]
        assert len(blocked_events) == 1

        payload = blocked_events[0].payload
        assert "reason" in payload
        assert "policy" in payload
        assert "current_usage" in payload
        assert "projected_tokens" in payload

        assert payload["policy"]["max_total_tokens"] == 3000
        assert payload["policy"]["max_llm_calls"] == 10
        assert payload["current_usage"]["total_tokens"] == 5000
        assert payload["current_usage"]["total_llm_calls"] == 1
        assert payload["projected_tokens"] == 2000

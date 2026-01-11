"""Budget enforcement gate for deterministic, crash-safe LLM budget control."""

from __future__ import annotations

from openchronicle.core.application.replay.usage_derivation import (
    UsageSummary,
    derive_usage,
)
from openchronicle.core.domain.models.budget_policy import BudgetPolicy
from openchronicle.core.domain.models.project import Event
from openchronicle.core.domain.ports.storage_port import StoragePort


class BudgetExceededError(Exception):
    """Raised when budget enforcement blocks execution."""


class BudgetGate:
    """
    Application-level budget enforcement gate.

    Runs before each LLM call attempt to ensure project stays within
    defined budget constraints. All decisions are explicit (no silent downgrades)
    and explainable via emitted events.

    Deterministic and crash-safe: enforcement is derived from persisted events,
    so it produces consistent results across restarts and retries.
    """

    def __init__(self, storage: StoragePort) -> None:
        """Initialize with storage backend."""
        self.storage = storage

    def check(
        self,
        project_id: str,
        policy: BudgetPolicy,
        projected_tokens: int | None = None,
    ) -> None:
        """
        Check if project is within budget before attempting LLM execution.

        If budget is exceeded, emits a budget.blocked event and raises BudgetExceededError.
        No silent downgrades; execution must fail explicitly.

        Args:
            project_id: Project identifier
            policy: BudgetPolicy with constraints
            projected_tokens: Estimated tokens for next LLM call (optional)

        Raises:
            BudgetExceededError: If any budget constraint is violated

        Side effects:
            Emits budget.blocked event if a constraint is violated.
        """
        # Quick path: no constraints defined
        if not policy.has_constraints():
            return

        # Derive current usage from persisted events
        usage = derive_usage(self.storage, project_id)

        # Check LLM call limit
        if policy.max_llm_calls is not None and usage.total_llm_calls >= policy.max_llm_calls:
            self._emit_blocked_event(
                project_id=project_id,
                policy=policy,
                usage=usage,
                projected_tokens=projected_tokens,
                reason="max_llm_calls",
            )
            raise BudgetExceededError(f"LLM call limit exceeded: {usage.total_llm_calls} >= {policy.max_llm_calls}")

        # Check token limit (if projected_tokens provided)
        if (
            policy.max_total_tokens is not None
            and projected_tokens is not None
            and usage.total_tokens + projected_tokens > policy.max_total_tokens
        ):
            self._emit_blocked_event(
                project_id=project_id,
                policy=policy,
                usage=usage,
                projected_tokens=projected_tokens,
                reason="max_total_tokens",
            )
            raise BudgetExceededError(
                f"Token budget exceeded: {usage.total_tokens} + {projected_tokens} > {policy.max_total_tokens}"
            )

    def _emit_blocked_event(
        self,
        project_id: str,
        policy: BudgetPolicy,
        usage: UsageSummary,
        projected_tokens: int | None,
        reason: str,
    ) -> None:
        """Emit budget.blocked event explaining why execution was blocked."""
        event = Event(
            project_id=project_id,
            task_id=None,
            agent_id=None,
            type="budget.blocked",
            payload={
                "project_id": project_id,
                "reason": reason,
                "policy": policy.to_dict(),
                "current_usage": {
                    "total_llm_calls": usage.total_llm_calls,
                    "total_tokens": usage.total_tokens,
                },
                "projected_tokens": projected_tokens,
            },
        )
        event.compute_hash()
        self.storage.append_event(event)

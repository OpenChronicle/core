"""Budget policy domain model for crash-safe enforcement.

Defines constraints on resource consumption (tokens, LLM calls) for a project.
Pure data model; no infrastructure or policy logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BudgetPolicy:
    """
    Project-level budget constraints for deterministic, crash-safe enforcement.

    Fields are optional; if not set, that constraint is not enforced.
    """

    max_total_tokens: int | None = None
    """Maximum total tokens (prompt + completion) across all LLM calls in project."""

    max_llm_calls: int | None = None
    """Maximum number of LLM execution attempts in project."""

    def has_constraints(self) -> bool:
        """Check if any constraints are defined."""
        return self.max_total_tokens is not None or self.max_llm_calls is not None

    def to_dict(self) -> dict:
        """Serialize for event payload."""
        return {
            "max_total_tokens": self.max_total_tokens,
            "max_llm_calls": self.max_llm_calls,
        }

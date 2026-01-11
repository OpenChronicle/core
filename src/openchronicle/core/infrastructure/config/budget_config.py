"""Load budget policy from environment variables."""

from __future__ import annotations

import contextlib
import os

from openchronicle.core.domain.models.budget_policy import BudgetPolicy


def load_budget_policy() -> BudgetPolicy:
    """
    Load budget policy from environment variables.

    Environment variables:
    - OC_BUDGET_MAX_TOKENS: Maximum total tokens (optional, int)
    - OC_BUDGET_MAX_CALLS: Maximum LLM calls (optional, int)

    Returns:
        BudgetPolicy with constraints from environment, or empty if none set
    """
    policy = BudgetPolicy()

    if max_tokens_str := os.getenv("OC_BUDGET_MAX_TOKENS"):
        with contextlib.suppress(ValueError):
            policy.max_total_tokens = int(max_tokens_str)

    if max_calls_str := os.getenv("OC_BUDGET_MAX_CALLS"):
        with contextlib.suppress(ValueError):
            policy.max_llm_calls = int(max_calls_str)

    return policy

"""Failure category classification for runtime failures.

This module provides a small, explicit set of failure categories to make
runtime failures clearer and more consistent. It maps internal error classes
(constraint, transient, refusal, permanent) to user-facing categories.

Categories are:
- PROVIDER_ERROR: Provider is unavailable, misconfigured, or returned a permanent error
- BUDGET_BLOCKED: Budget constraints prevented execution
- REFUSAL: Content policy rejected the prompt or response
- TIMEOUT: Operation exceeded time limit
- CONFIG_ERROR: Configuration or credential issue (subset of PROVIDER_ERROR)
- UNKNOWN: Unexpected or unclassifiable error

Rules:
- This is classification only; no logic changes
- Categories are metadata attached to events and results
- Internal error propagation is unchanged
"""

from __future__ import annotations

from typing import Literal

from openchronicle.core.domain.errors import BUDGET_EXCEEDED, TIMEOUT

# User-facing failure categories (what to display in CLI/events)
FailureCategory = Literal[
    "PROVIDER_ERROR",
    "BUDGET_BLOCKED",
    "REFUSAL",
    "TIMEOUT",
    "CONFIG_ERROR",
    "UNKNOWN",
]

# Map from internal ErrorClass to user-facing FailureCategory
ErrorClassToCategory = {
    "constraint": "BUDGET_BLOCKED",  # constraint = BudgetExceededError or RateLimitTimeoutError
    "transient": "TIMEOUT",  # transient = 429, 5xx, timeouts (user sees as timeout)
    "refusal": "REFUSAL",  # refusal = content policy violation
    "permanent": "PROVIDER_ERROR",  # permanent = all other provider errors (auth, config, etc.)
}


def classify_failure_category(error_code: str | None, error_class: str | None) -> FailureCategory:
    """Classify a failure into a user-facing category.

    Args:
        error_code: Internal error code (e.g., 'budget_exceeded', 'provider_error')
        error_class: Internal error class from error_classifier (constraint, transient, refusal, permanent)

    Returns:
        User-facing failure category
    """
    # Direct mapping by error code (most specific)
    if error_code == BUDGET_EXCEEDED:
        return "BUDGET_BLOCKED"
    if error_code == TIMEOUT:
        return "TIMEOUT"
    if error_code and "credential" in error_code.lower():
        return "CONFIG_ERROR"
    if error_code and "auth" in error_code.lower():
        return "CONFIG_ERROR"
    if error_code and "config" in error_code.lower():
        return "CONFIG_ERROR"

    # Fallback to error_class mapping
    if error_class and error_class in ErrorClassToCategory:
        return ErrorClassToCategory[error_class]  # type: ignore[return-value]

    # Default to UNKNOWN if nothing matches
    return "UNKNOWN"


def failure_category_description(category: FailureCategory) -> str:
    """Get human-readable description for a failure category.

    Args:
        category: Failure category

    Returns:
        Human-readable description
    """
    descriptions = {
        "PROVIDER_ERROR": "Provider error (unavailable, misconfigured, or permanent failure)",
        "BUDGET_BLOCKED": "Budget limit exceeded",
        "REFUSAL": "Content policy rejection",
        "TIMEOUT": "Operation timeout or rate limited",
        "CONFIG_ERROR": "Configuration or credential issue",
        "UNKNOWN": "Unexpected error",
    }
    return descriptions.get(category, "Unknown error")

"""Test error classification for LLM failures to ensure consistent fallback behavior."""

from __future__ import annotations

from openchronicle.core.application.policies.rate_limiter import RateLimitTimeoutError
from openchronicle.core.application.routing.error_classifier import classify_error
from openchronicle.core.domain.exceptions import BudgetExceededError
from openchronicle.core.domain.ports.llm_port import LLMProviderError


def test_content_policy_violation_classified_as_refusal() -> None:
    """Test that content_policy_violation error code is classified as refusal."""
    exc = LLMProviderError(
        "content blocked",
        status_code=400,
        error_code="content_policy_violation",
    )

    error_class = classify_error(exc)

    assert error_class == "refusal", "content_policy_violation must be classified as refusal"


def test_content_filter_classified_as_refusal() -> None:
    """Test that content_filter error code is classified as refusal."""
    exc = LLMProviderError(
        "content filtered",
        status_code=400,
        error_code="content_filter",
    )

    error_class = classify_error(exc)

    assert error_class == "refusal", "content_filter must be classified as refusal"


def test_safety_system_classified_as_refusal() -> None:
    """Test that safety_system error code is classified as refusal."""
    exc = LLMProviderError(
        "safety system triggered",
        status_code=400,
        error_code="safety_system",
    )

    error_class = classify_error(exc)

    assert error_class == "refusal", "safety_system must be classified as refusal"


def test_budget_exceeded_classified_as_constraint() -> None:
    """Test that BudgetExceededError is classified as constraint."""
    exc = BudgetExceededError(limit=500, current=1000, provider="test-provider", model="test-model")

    error_class = classify_error(exc)

    assert error_class == "constraint", "BudgetExceededError must be classified as constraint"


def test_rate_limit_timeout_classified_as_constraint() -> None:
    """Test that RateLimitTimeoutError is classified as constraint."""
    exc = RateLimitTimeoutError(
        max_wait_ms=3000,
        required_wait_ms=5000.0,
        provider="test-provider",
        model="test-model",
    )

    error_class = classify_error(exc)

    assert error_class == "constraint", "RateLimitTimeoutError must be classified as constraint"


def test_429_classified_as_transient() -> None:
    """Test that 429 status code is classified as transient."""
    exc = LLMProviderError(
        "Rate limit exceeded",
        status_code=429,
        error_code="rate_limit_exceeded",
    )

    error_class = classify_error(exc)

    assert error_class == "transient", "429 status code must be classified as transient"


def test_500_classified_as_transient() -> None:
    """Test that 5xx status codes are classified as transient."""
    exc = LLMProviderError(
        "Internal server error",
        status_code=500,
        error_code=None,
    )

    error_class = classify_error(exc)

    assert error_class == "transient", "500 status code must be classified as transient"


def test_401_classified_as_permanent() -> None:
    """Test that 401 authentication error is classified as permanent."""
    exc = LLMProviderError(
        "Invalid API key",
        status_code=401,
        error_code="invalid_api_key",
    )

    error_class = classify_error(exc)

    assert error_class == "permanent", "401 status code must be classified as permanent"


def test_generic_exception_classified_as_permanent() -> None:
    """Test that generic exceptions are classified as permanent."""
    exc = ValueError("Some unexpected error")

    error_class = classify_error(exc)

    assert error_class == "permanent", "Generic exceptions must be classified as permanent"

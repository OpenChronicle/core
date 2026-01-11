"""Task-level retry policy domain model.

Defines retry constraints for individual task execution.
Pure data model; no infrastructure or policy logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskRetryPolicy:
    """
    Task execution retry policy for deterministic, explicit retry decisions.

    All fields optional; defaults result in no retry behavior.
    """

    max_attempts: int = 1
    """Maximum execution attempts for this task (1 = no retry, 2 = one retry, etc.)."""

    retry_on_errors: list[str] | None = None
    """Error codes to retry on. If None, retry on any error (if max_attempts > 1).
    If list provided, only retry if error_code in this list."""

    backoff_seconds: int = 0
    """Delay before retry (metadata only; no actual sleep in this batch)."""

    def should_allow_retry(self) -> bool:
        """Check if retry is enabled by policy."""
        return self.max_attempts > 1

    def to_dict(self) -> dict:
        """Serialize for event payload."""
        return {
            "max_attempts": self.max_attempts,
            "retry_on_errors": self.retry_on_errors,
            "backoff_seconds": self.backoff_seconds,
        }

    @classmethod
    def no_retry(cls) -> TaskRetryPolicy:
        """Factory: policy with retries disabled (default)."""
        return cls(max_attempts=1, retry_on_errors=None, backoff_seconds=0)

    @classmethod
    def with_max_attempts(cls, max_attempts: int, backoff_seconds: int = 0) -> TaskRetryPolicy:
        """Factory: policy allowing retries on any error."""
        return cls(max_attempts=max_attempts, retry_on_errors=None, backoff_seconds=backoff_seconds)

    @classmethod
    def with_selective_retry(
        cls, max_attempts: int, retry_on_errors: list[str], backoff_seconds: int = 0
    ) -> TaskRetryPolicy:
        """Factory: policy allowing retries only on specific error codes."""
        return cls(max_attempts=max_attempts, retry_on_errors=retry_on_errors, backoff_seconds=backoff_seconds)

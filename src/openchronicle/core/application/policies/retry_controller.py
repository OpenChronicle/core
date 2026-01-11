"""Retry controller for deterministic, policy-driven retry decisions.

Decouples retry logic from orchestration; used to decide whether to retry a failed task.
No side effects; purely decision-oriented.
"""

from __future__ import annotations

from openchronicle.core.domain.models.retry_policy import TaskRetryPolicy


class RetryController:
    """Determines whether a task failure should trigger a retry based on policy."""

    @staticmethod
    def should_retry(
        *,
        task_id: str,
        attempt_id: str,
        error_code: str | None,
        policy: TaskRetryPolicy,
        prior_attempts: int,
    ) -> bool:
        """
        Decide whether to retry a failed task execution.

        Args:
            task_id: ID of the failed task (for context/logging)
            attempt_id: ID of the failed attempt (for context/logging)
            error_code: Error code from the failure (may be None)
            policy: Retry policy to consult
            prior_attempts: Number of attempts already made (not including the one that just failed)

        Returns:
            True if retry should be scheduled; False otherwise.

        Logic:
        1. If prior_attempts >= policy.max_attempts, we've exhausted attempts: return False
        2. If policy.retry_on_errors is set and error_code not in list: return False
        3. Otherwise: return True
        """
        # Check if we've exhausted our allotted attempts
        if prior_attempts >= policy.max_attempts:
            return False

        # If selective retry is configured, only retry on matching error codes
        return not (
            policy.retry_on_errors is not None and (error_code is None or error_code not in policy.retry_on_errors)
        )

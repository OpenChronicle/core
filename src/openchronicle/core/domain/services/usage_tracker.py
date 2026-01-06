"""LLM usage tracking service for token accounting and budget enforcement."""

from __future__ import annotations

from openchronicle.core.domain.models.project import LLMUsage
from openchronicle.core.domain.ports.llm_port import LLMResponse
from openchronicle.core.domain.ports.storage_port import StoragePort


class UsageTracker:
    """Service for recording and querying LLM usage metrics."""

    def __init__(self, storage: StoragePort) -> None:
        self.storage = storage

    def record_call(
        self,
        *,
        project_id: str,
        task_id: str,
        agent_id: str | None,
        response: LLMResponse,
    ) -> LLMUsage:
        """
        Record an LLM API call for usage tracking.

        Args:
            project_id: Project ID
            task_id: Task ID
            agent_id: Agent ID (optional)
            response: LLM response containing usage metrics

        Returns:
            Created LLMUsage record
        """
        usage_record = LLMUsage(
            project_id=project_id,
            task_id=task_id,
            agent_id=agent_id,
            provider=response.provider,
            model=response.model,
            request_id=response.request_id,
            input_tokens=response.usage.input_tokens if response.usage else None,
            output_tokens=response.usage.output_tokens if response.usage else None,
            total_tokens=response.usage.total_tokens if response.usage else None,
            latency_ms=response.latency_ms,
        )

        self.storage.insert_llm_usage(usage_record)
        return usage_record

    def get_task_token_totals(self, task_id: str) -> dict[str, int]:
        """
        Get cumulative token totals for a task.

        Args:
            task_id: Task ID

        Returns:
            Dict with input_tokens, output_tokens, total_tokens
        """
        result: dict[str, int] = self.storage.sum_tokens_by_task(task_id)
        return result

"""Derive LLM usage from replayed events for crash-safe budget enforcement."""

from __future__ import annotations

from dataclasses import dataclass

from openchronicle.core.domain.ports.storage_port import StoragePort


@dataclass
class UsageSummary:
    """
    Deterministic summary of current LLM resource consumption.

    Derived from persisted events; crash-safe because it reconstructs from the log.
    """

    total_llm_calls: int = 0
    """Count of completed LLM executions (from llm.execution_recorded events)."""

    total_tokens: int = 0
    """Total tokens consumed (prompt + completion)."""


def derive_usage(storage: StoragePort, project_id: str) -> UsageSummary:
    """
    Derive current LLM usage from replayed events.

    Counts llm.execution_recorded events as authoritative source of execution attempts.
    Uses total_tokens if present; otherwise computes from prompt_tokens + completion_tokens.

    This function is deterministic and crash-safe:
    - Results depend only on persisted events
    - Consistent across restarts and retries
    - No external state or RPC calls

    Args:
        storage: Storage backend with event log
        project_id: Project identifier

    Returns:
        UsageSummary with total calls and tokens
    """
    summary = UsageSummary()

    # Load all events for this project (already deterministically ordered)
    events = storage.list_events(project_id=project_id)

    # Process only llm.execution_recorded events
    for event in events:
        if event.type == "llm.execution_recorded":
            summary.total_llm_calls += 1

            # Extract tokens from payload
            payload = event.payload or {}

            # Prefer total_tokens if present
            if "total_tokens" in payload and payload["total_tokens"] is not None:
                tokens = payload["total_tokens"]
            else:
                # Compute from prompt + completion
                prompt_tokens = payload.get("prompt_tokens") or 0
                completion_tokens = payload.get("completion_tokens") or 0
                tokens = prompt_tokens + completion_tokens

            summary.total_tokens += tokens

    return summary

"""LLM-based consistency checker for storytelling content.

Detects contradictions between new content and established story context.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyIssue:
    """A single consistency issue detected."""

    severity: str  # "error", "warning", "info"
    description: str
    entity_type: str  # "character", "location", "event", etc.
    entity_name: str
    conflicting_memories: list[str] = field(default_factory=list)


@dataclass
class ConsistencyReport:
    """Report from a consistency check."""

    issues: list[ConsistencyIssue] = field(default_factory=list)
    checked_items: int = 0
    passed: bool = True
    summary: str = ""


async def check_consistency(
    memory_search: Any,
    llm_complete: Any,
    content: str,
    content_type: str = "scene",
    *,
    max_context_items: int = 20,
    temperature: float = 0.2,
) -> ConsistencyReport:
    """Check content for consistency against existing story context.

    1. Assemble story context (characters, locations, scenes) via memory_search
    2. Ask LLM to identify contradictions in the new content
    3. Parse JSON response into ConsistencyReport

    Args:
        memory_search: Handler context's memory_search closure.
        llm_complete: Handler context's llm_complete closure.
        content: The new content to validate.
        content_type: Type of content being checked.
        max_context_items: Maximum context items to retrieve.
        temperature: LLM temperature (low for precision).
    """
    # 1. Assemble context
    context_items: list[str] = []
    for tag_set in [
        ["story", "character"],
        ["story", "location"],
        ["story", "scene"],
        ["story", "worldbuilding"],
    ]:
        items = memory_search(content[:200], top_k=max_context_items // 4, tags=tag_set)
        for item in items:
            context_items.append(item.content)

    if not context_items:
        return ConsistencyReport(
            checked_items=0,
            passed=True,
            summary="No story context available for consistency checking.",
        )

    # 2. Ask LLM
    context_block = "\n---\n".join(context_items)
    prompt = (
        f"Established story context:\n{context_block}\n\n"
        f"New {content_type} content to validate:\n{content}\n\n"
        "Identify any contradictions, inconsistencies, or factual conflicts "
        "between the new content and the established context. "
        "Return a JSON object with:\n"
        '- "issues": array of {"severity": "error"|"warning"|"info", '
        '"description": "...", "entity_type": "...", "entity_name": "..."}\n'
        '- "summary": brief overall assessment\n'
        "If no issues found, return an empty issues array."
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a consistency checker for an interactive story. "
                "Your job is to find contradictions between new content and "
                "established story facts. Be precise and cite specific conflicts. "
                "Return ONLY valid JSON."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = await llm_complete(messages, max_output_tokens=1024, temperature=temperature)

    # 3. Parse response
    return _parse_consistency_response(response.content, len(context_items))


async def validate_scene_consistency(
    memory_search: Any,
    llm_complete: Any,
    scene_text: str,
) -> ConsistencyReport:
    """Convenience wrapper for scene-specific consistency checking."""
    return await check_consistency(memory_search, llm_complete, scene_text, content_type="scene")


def _parse_consistency_response(content: str, checked_items: int) -> ConsistencyReport:
    """Parse LLM response into ConsistencyReport."""
    content = content.strip()

    # Handle markdown code fences
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse consistency check JSON response")
        return ConsistencyReport(
            checked_items=checked_items,
            passed=True,
            summary="Unable to parse consistency check response.",
        )

    if not isinstance(data, dict):
        return ConsistencyReport(checked_items=checked_items, passed=True, summary="Invalid response format.")

    issues: list[ConsistencyIssue] = []
    for item in data.get("issues", []):
        if isinstance(item, dict):
            issues.append(
                ConsistencyIssue(
                    severity=str(item.get("severity", "info")),
                    description=str(item.get("description", "")),
                    entity_type=str(item.get("entity_type", "")),
                    entity_name=str(item.get("entity_name", "")),
                )
            )

    has_errors = any(i.severity == "error" for i in issues)
    summary = data.get("summary", "")

    return ConsistencyReport(
        issues=issues,
        checked_items=checked_items,
        passed=not has_errors,
        summary=summary,
    )

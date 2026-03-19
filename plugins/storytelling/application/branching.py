"""LLM-driven narrative branching based on resolution outcomes.

Generates story branch options after a dice resolution, using the outcome
to seed narrative consequences.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ..domain.mechanics import OutcomeType, ResolutionResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NarrativeBranch:
    """A single narrative branch option."""

    description: str
    consequence_type: str
    transition_hint: str


@dataclass
class BranchOptions:
    """Collection of narrative branches following a resolution."""

    resolution_result: ResolutionResult
    branches: list[NarrativeBranch] = field(default_factory=list)


# Template seeds for LLM prompt construction per outcome type.
OUTCOME_TEMPLATES: dict[OutcomeType, dict[str, str]] = {
    OutcomeType.CRITICAL_SUCCESS: {
        "consequence": "spectacular success with bonus effect",
        "transition": "The character exceeds expectations dramatically",
    },
    OutcomeType.SUCCESS: {
        "consequence": "clean success, objective achieved",
        "transition": "The character accomplishes their goal",
    },
    OutcomeType.PARTIAL_SUCCESS: {
        "consequence": "success with complication or cost",
        "transition": "The character succeeds but at a price",
    },
    OutcomeType.FAILURE: {
        "consequence": "failure with consequences",
        "transition": "The character fails and faces setback",
    },
    OutcomeType.CRITICAL_FAILURE: {
        "consequence": "catastrophic failure with lasting impact",
        "transition": "Everything goes wrong in the worst way",
    },
}


async def generate_branches(
    llm_complete: Any,
    resolution_result: ResolutionResult,
    story_context_summary: str = "",
    *,
    branch_count: int = 3,
    temperature: float = 0.9,
) -> BranchOptions:
    """Generate narrative branch options using LLM.

    Args:
        llm_complete: Handler context's llm_complete closure.
        resolution_result: The dice resolution that drives the branching.
        story_context_summary: Brief summary of current story state.
        branch_count: Number of branches to generate.
        temperature: LLM temperature (higher = more creative).
    """
    template = OUTCOME_TEMPLATES.get(
        resolution_result.outcome,
        {"consequence": "uncertain outcome", "transition": "The situation shifts"},
    )

    prompt = _build_branch_prompt(resolution_result, template, story_context_summary, branch_count)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a narrative branching engine for an interactive story. "
                "Generate story branch options as a JSON array. Each branch has: "
                '"description" (2-3 sentences), "consequence_type" (1-2 words), '
                '"transition_hint" (1 sentence). Return ONLY valid JSON.'
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = await llm_complete(messages, max_output_tokens=1024, temperature=temperature)

    branches = _parse_branches(response.content)
    return BranchOptions(resolution_result=resolution_result, branches=branches)


def _build_branch_prompt(
    result: ResolutionResult,
    template: dict[str, str],
    context_summary: str,
    branch_count: int,
) -> str:
    """Build the LLM prompt for branch generation."""
    parts = [
        f"Resolution: {result.resolution_type.value}",
        f"Outcome: {result.outcome.value} (margin: {result.success_margin:+d})",
        f"Expected consequence: {template['consequence']}",
        f"Transition seed: {template['transition']}",
    ]
    if result.character_name:
        parts.append(f"Character: {result.character_name}")
    if context_summary:
        parts.append(f"Story context: {context_summary}")
    parts.append(f"Generate exactly {branch_count} narrative branch options.")
    return "\n".join(parts)


def _parse_branches(content: str) -> list[NarrativeBranch]:
    """Parse LLM response into NarrativeBranch objects."""
    # Try to extract JSON array from response
    content = content.strip()

    # Handle markdown code fences
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last fence lines
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse branch JSON from LLM response")
        return []

    if not isinstance(data, list):
        return []

    branches = []
    for item in data:
        if isinstance(item, dict):
            branches.append(
                NarrativeBranch(
                    description=str(item.get("description", "")),
                    consequence_type=str(item.get("consequence_type", "")),
                    transition_hint=str(item.get("transition_hint", "")),
                )
            )
    return branches

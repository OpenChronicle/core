"""Memory-backed character stat management.

Loads and saves stat blocks as tagged memory items. Stat blocks are stored
as human-readable + JSON-parseable content.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..domain.mechanics import ResolutionType
from ..domain.stats import RESOLUTION_STAT_MAP, StatBlock, StatProgression, StatType

logger = logging.getLogger(__name__)

# Tags used for stat block memories
STAT_TAGS = ["story", "character-stats"]


def _parse_stat_block_content(content: str) -> dict[str, int] | None:
    """Extract JSON stat values from a stat block memory."""
    # Look for a JSON object line in the content
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    return {k: int(v) for k, v in data.items()}
            except (json.JSONDecodeError, ValueError):
                continue
    return None


def _format_stat_block_content(
    character_name: str,
    stat_block: StatBlock,
    progressions: list[StatProgression] | None = None,
) -> str:
    """Format a stat block as memory content."""
    values_json = json.dumps(stat_block.values, indent=None)
    lines = [
        f"[Character Stats] {character_name}",
        "",
        values_json,
    ]
    if progressions:
        lines.append("")
        lines.append("Progression:")
        for p in progressions:
            lines.append(f"- {p.stat_type.value}: {p.old_value} -> {p.new_value} ({p.reason})")
    return "\n".join(lines)


def load_stat_block(
    memory_search: Any,
    character_name: str,
) -> StatBlock | None:
    """Load a character's stat block from memory.

    Args:
        memory_search: Handler context's memory_search closure.
        character_name: Character name to search for.

    Returns:
        StatBlock if found, None otherwise.
    """
    items = memory_search(
        f"character stats {character_name}",
        top_k=5,
        tags=STAT_TAGS,
    )
    for item in items:
        # Match by character name in content header
        if character_name.lower() in item.content.lower():
            values = _parse_stat_block_content(item.content)
            if values is not None:
                return StatBlock(values=values)
    return None


def save_stat_block(
    memory_save: Any,
    character_name: str,
    stat_block: StatBlock,
    progressions: list[StatProgression] | None = None,
) -> str:
    """Save a character's stat block to memory.

    Returns the memory ID of the saved item.
    """
    content = _format_stat_block_content(character_name, stat_block, progressions)
    result = memory_save(content=content, tags=STAT_TAGS)
    logger.info("Saved stat block for %s: %s", character_name, result.id)
    return str(result.id)


def update_stat(
    memory_search: Any,
    memory_save: Any,
    memory_update: Any,
    character_name: str,
    stat_type: StatType,
    new_value: int,
    reason: str,
) -> StatBlock:
    """Update a single stat for a character, preserving progression history.

    If no existing stat block is found, creates a new one with the given stat.
    """
    existing = load_stat_block(memory_search, character_name)
    if existing is None:
        existing = StatBlock()

    old_value = existing.values.get(stat_type.value, 10)
    updated = existing.with_update(stat_type, new_value)

    progression = StatProgression(
        stat_type=stat_type,
        old_value=old_value,
        new_value=max(1, min(20, new_value)),
        reason=reason,
    )

    # Load existing progressions from memory (if any)
    progressions = _load_existing_progressions(memory_search, character_name)
    progressions.append(progression)

    # Delete old stat block and save new one
    save_stat_block(memory_save, character_name, updated, progressions)
    return updated


def _load_existing_progressions(
    memory_search: Any,
    character_name: str,
) -> list[StatProgression]:
    """Parse existing progressions from a stat block memory."""
    items = memory_search(
        f"character stats {character_name}",
        top_k=5,
        tags=STAT_TAGS,
    )
    progressions: list[StatProgression] = []
    prog_re = re.compile(r"^- (\w+): (\d+) -> (\d+) \((.+)\)$")

    for item in items:
        if character_name.lower() not in item.content.lower():
            continue
        in_progression = False
        for line in item.content.split("\n"):
            if line.strip() == "Progression:":
                in_progression = True
                continue
            if in_progression:
                match = prog_re.match(line.strip())
                if match:
                    try:
                        stat = StatType(match.group(1))
                        progressions.append(
                            StatProgression(
                                stat_type=stat,
                                old_value=int(match.group(2)),
                                new_value=int(match.group(3)),
                                reason=match.group(4),
                            )
                        )
                    except ValueError:
                        continue
    return progressions


def get_stat_modifier_for_resolution(
    stat_block: StatBlock,
    resolution_type: ResolutionType,
) -> int:
    """Get the stat modifier for a resolution type from a stat block."""
    stat_type = RESOLUTION_STAT_MAP.get(resolution_type)
    if stat_type is None:
        return 0
    return stat_block.modifier(stat_type)

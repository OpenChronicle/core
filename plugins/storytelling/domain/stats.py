"""Character stat system for the game mechanics engine.

Pure domain models — stat types, categories, and stat blocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .mechanics import ResolutionType


class StatCategory(Enum):
    """Stat categories."""

    PHYSICAL = "physical"
    MENTAL = "mental"
    SOCIAL = "social"
    EMOTIONAL = "emotional"
    MORAL = "moral"


class StatType(Enum):
    """Individual stat types."""

    # Physical
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    # Mental
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CREATIVITY = "creativity"
    PERCEPTION = "perception"
    # Social
    CHARISMA = "charisma"
    HUMOR = "humor"
    EMPATHY = "empathy"
    # Emotional
    WILLPOWER = "willpower"
    COURAGE = "courage"
    TEMPER = "temper"
    # Moral
    LOYALTY = "loyalty"
    GREED = "greed"


STAT_CATEGORIES: dict[StatCategory, tuple[StatType, ...]] = {
    StatCategory.PHYSICAL: (StatType.STRENGTH, StatType.DEXTERITY),
    StatCategory.MENTAL: (
        StatType.INTELLIGENCE,
        StatType.WISDOM,
        StatType.CREATIVITY,
        StatType.PERCEPTION,
    ),
    StatCategory.SOCIAL: (StatType.CHARISMA, StatType.HUMOR, StatType.EMPATHY),
    StatCategory.EMOTIONAL: (StatType.WILLPOWER, StatType.COURAGE, StatType.TEMPER),
    StatCategory.MORAL: (StatType.LOYALTY, StatType.GREED),
}

# Maps resolution types to their primary stat for modifier lookup.
RESOLUTION_STAT_MAP: dict[ResolutionType, StatType] = {
    ResolutionType.SKILL_CHECK: StatType.DEXTERITY,
    ResolutionType.COMBAT_ACTION: StatType.STRENGTH,
    ResolutionType.SOCIAL_INTERACTION: StatType.CHARISMA,
    ResolutionType.EXPLORATION: StatType.PERCEPTION,
    ResolutionType.CREATIVE_ACTION: StatType.CREATIVITY,
    ResolutionType.MENTAL_CHALLENGE: StatType.INTELLIGENCE,
    ResolutionType.PHYSICAL_CHALLENGE: StatType.STRENGTH,
    ResolutionType.MAGICAL_ACTION: StatType.WISDOM,
    ResolutionType.STEALTH_ACTION: StatType.DEXTERITY,
    ResolutionType.SURVIVAL_ACTION: StatType.WISDOM,
    ResolutionType.LUCK_CHECK: StatType.WISDOM,
    ResolutionType.NARRATIVE_CHOICE: StatType.CHARISMA,
    ResolutionType.CHARACTER_DEVELOPMENT: StatType.WILLPOWER,
}


@dataclass(frozen=True)
class StatBlock:
    """Immutable character stat block.

    Values are stored as ``{stat_value: int}`` where stat_value is the
    ``StatType.value`` string (e.g. ``"strength"``).  Range is 1-20.
    """

    values: dict[str, int] = field(default_factory=dict)

    def modifier(self, stat: StatType) -> int:
        """D&D-style modifier: ``(value - 10) // 2``."""
        val = self.values.get(stat.value, 10)
        return (val - 10) // 2

    def with_update(self, stat: StatType, value: int) -> StatBlock:
        """Return a new StatBlock with one stat changed."""
        clamped = max(1, min(20, value))
        new_values = dict(self.values)
        new_values[stat.value] = clamped
        return StatBlock(values=new_values)


@dataclass(frozen=True)
class StatProgression:
    """Records a single stat change for history tracking."""

    stat_type: StatType
    old_value: int
    new_value: int
    reason: str

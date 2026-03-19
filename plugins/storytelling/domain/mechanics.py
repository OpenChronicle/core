"""Domain models for the game mechanics engine.

Pure value objects with zero external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DiceType(Enum):
    """Dice types supported by the engine."""

    D4 = "d4"
    D6 = "d6"
    D8 = "d8"
    D10 = "d10"
    D12 = "d12"
    D20 = "d20"
    D100 = "d100"
    FUDGE = "fudge"
    COIN = "coin"


# Map DiceType to number of faces (max value per die).
DICE_FACES: dict[DiceType, int] = {
    DiceType.D4: 4,
    DiceType.D6: 6,
    DiceType.D8: 8,
    DiceType.D10: 10,
    DiceType.D12: 12,
    DiceType.D20: 20,
    DiceType.D100: 100,
    # Fudge: -1, 0, +1  — handled specially
    # Coin: 0/1 — handled specially
}


class ResolutionType(Enum):
    """Types of action resolution."""

    SKILL_CHECK = "skill_check"
    COMBAT_ACTION = "combat_action"
    SOCIAL_INTERACTION = "social_interaction"
    EXPLORATION = "exploration"
    CREATIVE_ACTION = "creative_action"
    MENTAL_CHALLENGE = "mental_challenge"
    PHYSICAL_CHALLENGE = "physical_challenge"
    MAGICAL_ACTION = "magical_action"
    STEALTH_ACTION = "stealth_action"
    SURVIVAL_ACTION = "survival_action"
    LUCK_CHECK = "luck_check"
    NARRATIVE_CHOICE = "narrative_choice"
    CHARACTER_DEVELOPMENT = "character_development"


class DifficultyLevel(Enum):
    """Difficulty levels with their associated DCs (difficulty class)."""

    TRIVIAL = 5
    EASY = 10
    MODERATE = 15
    HARD = 20
    VERY_HARD = 25
    LEGENDARY = 30


class OutcomeType(Enum):
    """Result outcomes from action resolution."""

    CRITICAL_SUCCESS = "critical_success"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    CRITICAL_FAILURE = "critical_failure"


@dataclass(frozen=True)
class DiceRoll:
    """Result of rolling one or more dice."""

    dice_type: DiceType
    rolls: tuple[int, ...]
    modifier: int = 0
    advantage: bool = False
    disadvantage: bool = False

    @property
    def total(self) -> int:
        return sum(self.rolls) + self.modifier


@dataclass(frozen=True)
class ResolutionResult:
    """Result from resolving a game action."""

    resolution_type: ResolutionType
    outcome: OutcomeType
    dice_roll: DiceRoll
    difficulty_check: int
    success_margin: int
    character_name: str | None = None
    character_modifier: int = 0

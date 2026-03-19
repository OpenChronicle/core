"""Action resolution engine — stateless resolution against difficulty checks.

All functions are pure. RNG is injectable for determinism.
"""

from __future__ import annotations

from random import Random

from ..domain.mechanics import (
    DiceType,
    DifficultyLevel,
    OutcomeType,
    ResolutionResult,
    ResolutionType,
)
from .dice_engine import roll_dice

# Difficulty Class values by level
DIFFICULTY_DC: dict[DifficultyLevel, int] = {level: level.value for level in DifficultyLevel}


def determine_outcome(
    total: int,
    dc: int,
    natural_roll: int | None = None,
    dice_type: DiceType = DiceType.D20,
) -> OutcomeType:
    """Determine outcome from a roll total against a DC.

    Special rules for D20:
    - Natural 20 → CRITICAL_SUCCESS
    - Natural 1 → CRITICAL_FAILURE

    General threshold logic:
    - total >= dc + 5 → SUCCESS
    - total >= dc → PARTIAL_SUCCESS
    - total >= dc - 3 → FAILURE
    - total < dc - 3 → CRITICAL_FAILURE
    """
    # D20 natural crit checks
    if dice_type == DiceType.D20 and natural_roll is not None:
        if natural_roll == 20:
            return OutcomeType.CRITICAL_SUCCESS
        if natural_roll == 1:
            return OutcomeType.CRITICAL_FAILURE

    if total >= dc + 5:
        return OutcomeType.SUCCESS
    if total >= dc:
        return OutcomeType.PARTIAL_SUCCESS
    if total >= dc - 3:
        return OutcomeType.FAILURE
    return OutcomeType.CRITICAL_FAILURE


def resolve_action(
    resolution_type: ResolutionType,
    difficulty: DifficultyLevel,
    character_modifier: int = 0,
    *,
    advantage: bool = False,
    disadvantage: bool = False,
    dice_type: DiceType = DiceType.D20,
    rng: Random | None = None,
) -> ResolutionResult:
    """Resolve a game action against a difficulty check.

    Args:
        resolution_type: What kind of action is being attempted.
        difficulty: How hard the action is.
        character_modifier: Stat-derived modifier to add to the roll.
        advantage: Roll with advantage (D20 only).
        disadvantage: Roll with disadvantage (D20 only).
        dice_type: Die to roll (default D20).
        rng: Random instance for deterministic results.
    """
    dc = DIFFICULTY_DC[difficulty]

    dice_roll = roll_dice(
        dice_type,
        count=1,
        modifier=character_modifier,
        advantage=advantage,
        disadvantage=disadvantage,
        rng=rng,
    )

    # Extract the natural roll (before modifier) for crit detection
    natural_roll = dice_roll.rolls[0] if dice_roll.rolls else None

    outcome = determine_outcome(dice_roll.total, dc, natural_roll, dice_type)
    success_margin = dice_roll.total - dc

    return ResolutionResult(
        resolution_type=resolution_type,
        outcome=outcome,
        dice_roll=dice_roll,
        difficulty_check=dc,
        success_margin=success_margin,
        character_modifier=character_modifier,
    )

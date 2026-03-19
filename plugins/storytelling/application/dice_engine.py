"""Dice engine — pure computation with injectable RNG.

All functions are stateless and deterministic given the same ``rng``.
"""

from __future__ import annotations

import re
from random import Random

from ..domain.mechanics import DICE_FACES, DiceRoll, DiceType

# Regex for standard dice notation: "3d6+2", "d20", "2d8-1", "d100"
_NOTATION_RE = re.compile(
    r"^(?P<count>\d+)?d(?P<faces>\d+)(?P<mod>[+-]\d+)?$",
    re.IGNORECASE,
)

# Aliases for special dice types
_ALIASES: dict[str, DiceType] = {
    "fudge": DiceType.FUDGE,
    "df": DiceType.FUDGE,
    "coin": DiceType.COIN,
    "flip": DiceType.COIN,
}


def roll_dice(
    dice_type: DiceType,
    count: int = 1,
    modifier: int = 0,
    *,
    advantage: bool = False,
    disadvantage: bool = False,
    rng: Random | None = None,
) -> DiceRoll:
    """Roll dice of the given type.

    Args:
        dice_type: Type of die to roll.
        count: Number of dice to roll.
        modifier: Flat modifier added to the total.
        advantage: Roll twice, keep the higher (D20 only, count=1).
        disadvantage: Roll twice, keep the lower (D20 only, count=1).
        rng: Random instance for deterministic results.
    """
    rng = rng or Random()  # noqa: S311
    count = max(1, count)

    if dice_type == DiceType.FUDGE:
        rolls = tuple(rng.choice((-1, 0, 1)) for _ in range(count))
    elif dice_type == DiceType.COIN:
        rolls = tuple(rng.choice((0, 1)) for _ in range(count))
    else:
        faces = DICE_FACES[dice_type]
        if (advantage or disadvantage) and dice_type == DiceType.D20 and count == 1:
            r1 = rng.randint(1, faces)
            r2 = rng.randint(1, faces)
            rolls = (max(r1, r2),) if advantage else (min(r1, r2),)
            return DiceRoll(
                dice_type=dice_type,
                rolls=rolls,
                modifier=modifier,
                advantage=advantage,
                disadvantage=disadvantage,
            )
        rolls = tuple(rng.randint(1, faces) for _ in range(count))

    return DiceRoll(
        dice_type=dice_type,
        rolls=rolls,
        modifier=modifier,
        advantage=advantage,
        disadvantage=disadvantage,
    )


def parse_dice_notation(notation: str) -> tuple[int, DiceType, int]:
    """Parse dice notation string into (count, DiceType, modifier).

    Supports: "3d6+2", "d20", "2d8-1", "d100", "fudge", "coin"

    Raises:
        ValueError: If notation is not recognized.
    """
    clean = notation.strip().lower()

    # Check aliases first
    if clean in _ALIASES:
        return (1, _ALIASES[clean], 0)

    match = _NOTATION_RE.match(clean)
    if not match:
        raise ValueError(f"Invalid dice notation: '{notation}'")

    count = int(match.group("count") or "1")
    faces = int(match.group("faces"))
    mod = int(match.group("mod") or "0")

    # Map faces to DiceType
    faces_to_type: dict[int, DiceType] = {v: k for k, v in DICE_FACES.items()}
    dice_type = faces_to_type.get(faces)
    if dice_type is None:
        raise ValueError(f"Unsupported die type: d{faces}")

    return (count, dice_type, mod)


def roll_notation(
    notation: str,
    *,
    advantage: bool = False,
    disadvantage: bool = False,
    rng: Random | None = None,
) -> DiceRoll:
    """Convenience: parse notation and roll in one call."""
    count, dice_type, modifier = parse_dice_notation(notation)
    return roll_dice(
        dice_type,
        count,
        modifier,
        advantage=advantage,
        disadvantage=disadvantage,
        rng=rng,
    )

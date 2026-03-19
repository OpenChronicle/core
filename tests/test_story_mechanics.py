"""Tests for storytelling game mechanics — dice, resolution, stats, branching."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from random import Random
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from plugins.storytelling.application.dice_engine import (
    parse_dice_notation,
    roll_dice,
    roll_notation,
)
from plugins.storytelling.application.resolution import (
    DIFFICULTY_DC,
    determine_outcome,
    resolve_action,
)
from plugins.storytelling.application.stat_manager import (
    _format_stat_block_content,
    _parse_stat_block_content,
    get_stat_modifier_for_resolution,
    load_stat_block,
    save_stat_block,
)
from plugins.storytelling.domain.mechanics import (
    DICE_FACES,
    DiceRoll,
    DiceType,
    DifficultyLevel,
    OutcomeType,
    ResolutionResult,
    ResolutionType,
)
from plugins.storytelling.domain.stats import (
    RESOLUTION_STAT_MAP,
    STAT_CATEGORIES,
    StatBlock,
    StatCategory,
    StatProgression,
    StatType,
)

# ===========================================================================
# Helpers
# ===========================================================================


@dataclass
class FakeMemoryItem:
    id: str
    content: str
    tags: list[str]
    pinned: bool = False


@dataclass
class FakeLLMResponse:
    content: str
    provider: str = "stub"
    model: str = "stub-model"
    finish_reason: str = "stop"


def _make_search(items: list[FakeMemoryItem] | None = None) -> Any:
    items = items or []

    def search(query: str, top_k: int = 8, tags: list[str] | None = None) -> list[FakeMemoryItem]:
        results = items
        if tags:
            results = [i for i in results if all(t in i.tags for t in tags)]
        return results[:top_k]

    return search


def _make_save() -> MagicMock:
    mock = MagicMock()
    mock.return_value = FakeMemoryItem(id="saved-001", content="", tags=[])
    return mock


# ===========================================================================
# Dice Engine Tests
# ===========================================================================


class TestDiceType:
    def test_all_nine_types(self) -> None:
        assert len(DiceType) == 9

    def test_faces_map_covers_standard_dice(self) -> None:
        for dt in (DiceType.D4, DiceType.D6, DiceType.D8, DiceType.D10, DiceType.D12, DiceType.D20, DiceType.D100):
            assert dt in DICE_FACES


class TestRollDice:
    def test_d20_in_range(self) -> None:
        rng = Random(42)
        for _ in range(100):
            result = roll_dice(DiceType.D20, rng=rng)
            assert 1 <= result.rolls[0] <= 20

    def test_d6_in_range(self) -> None:
        rng = Random(42)
        for _ in range(100):
            result = roll_dice(DiceType.D6, rng=rng)
            assert 1 <= result.rolls[0] <= 6

    def test_d4_in_range(self) -> None:
        rng = Random(42)
        for _ in range(50):
            result = roll_dice(DiceType.D4, rng=rng)
            assert 1 <= result.rolls[0] <= 4

    def test_d8_in_range(self) -> None:
        rng = Random(42)
        for _ in range(50):
            result = roll_dice(DiceType.D8, rng=rng)
            assert 1 <= result.rolls[0] <= 8

    def test_d10_in_range(self) -> None:
        rng = Random(42)
        for _ in range(50):
            result = roll_dice(DiceType.D10, rng=rng)
            assert 1 <= result.rolls[0] <= 10

    def test_d12_in_range(self) -> None:
        rng = Random(42)
        for _ in range(50):
            result = roll_dice(DiceType.D12, rng=rng)
            assert 1 <= result.rolls[0] <= 12

    def test_d100_in_range(self) -> None:
        rng = Random(42)
        for _ in range(50):
            result = roll_dice(DiceType.D100, rng=rng)
            assert 1 <= result.rolls[0] <= 100

    def test_multiple_dice(self) -> None:
        result = roll_dice(DiceType.D6, count=3, rng=Random(42))
        assert len(result.rolls) == 3
        assert all(1 <= r <= 6 for r in result.rolls)

    def test_modifier_added(self) -> None:
        result = roll_dice(DiceType.D6, count=1, modifier=5, rng=Random(42))
        assert result.total == result.rolls[0] + 5

    def test_negative_modifier(self) -> None:
        result = roll_dice(DiceType.D20, modifier=-3, rng=Random(42))
        assert result.total == result.rolls[0] - 3

    def test_fudge_values(self) -> None:
        rng = Random(42)
        for _ in range(100):
            result = roll_dice(DiceType.FUDGE, rng=rng)
            assert result.rolls[0] in (-1, 0, 1)

    def test_coin_values(self) -> None:
        rng = Random(42)
        for _ in range(100):
            result = roll_dice(DiceType.COIN, rng=rng)
            assert result.rolls[0] in (0, 1)

    def test_advantage_keeps_higher(self) -> None:
        # Seed that produces a predictable pair
        rng = Random(42)
        result = roll_dice(DiceType.D20, advantage=True, rng=rng)
        assert result.advantage is True
        assert len(result.rolls) == 1  # Only the kept roll

    def test_disadvantage_keeps_lower(self) -> None:
        rng = Random(42)
        result = roll_dice(DiceType.D20, disadvantage=True, rng=rng)
        assert result.disadvantage is True
        assert len(result.rolls) == 1

    def test_advantage_always_gte_single(self) -> None:
        """Advantage should produce results >= plain roll on average (statistical)."""
        rng_adv = Random(12345)
        rng_plain = Random(12345)
        adv_sum = sum(roll_dice(DiceType.D20, advantage=True, rng=rng_adv).total for _ in range(1000))
        plain_sum = sum(roll_dice(DiceType.D20, rng=rng_plain).total for _ in range(1000))
        # Advantage should average higher (statistically very likely)
        assert adv_sum > plain_sum

    def test_deterministic_with_seed(self) -> None:
        r1 = roll_dice(DiceType.D20, rng=Random(99))
        r2 = roll_dice(DiceType.D20, rng=Random(99))
        assert r1.rolls == r2.rolls

    def test_total_is_sum_plus_modifier(self) -> None:
        result = roll_dice(DiceType.D6, count=3, modifier=2, rng=Random(42))
        assert result.total == sum(result.rolls) + 2

    def test_count_minimum_one(self) -> None:
        result = roll_dice(DiceType.D6, count=0, rng=Random(42))
        assert len(result.rolls) == 1


class TestParseDiceNotation:
    def test_simple_d20(self) -> None:
        count, dt, mod = parse_dice_notation("d20")
        assert count == 1
        assert dt == DiceType.D20
        assert mod == 0

    def test_3d6_plus_2(self) -> None:
        count, dt, mod = parse_dice_notation("3d6+2")
        assert count == 3
        assert dt == DiceType.D6
        assert mod == 2

    def test_2d8_minus_1(self) -> None:
        count, dt, mod = parse_dice_notation("2d8-1")
        assert count == 2
        assert dt == DiceType.D8
        assert mod == -1

    def test_d100(self) -> None:
        count, dt, mod = parse_dice_notation("d100")
        assert count == 1
        assert dt == DiceType.D100

    def test_fudge_alias(self) -> None:
        count, dt, mod = parse_dice_notation("fudge")
        assert dt == DiceType.FUDGE

    def test_coin_alias(self) -> None:
        count, dt, mod = parse_dice_notation("coin")
        assert dt == DiceType.COIN

    def test_case_insensitive(self) -> None:
        count, dt, mod = parse_dice_notation("D20")
        assert dt == DiceType.D20

    def test_invalid_notation(self) -> None:
        with pytest.raises(ValueError, match="Invalid dice notation"):
            parse_dice_notation("xyz")

    def test_unsupported_die(self) -> None:
        with pytest.raises(ValueError, match="Unsupported die type"):
            parse_dice_notation("d7")


class TestRollNotation:
    def test_convenience_roll(self) -> None:
        result = roll_notation("3d6+2", rng=Random(42))
        assert result.dice_type == DiceType.D6
        assert len(result.rolls) == 3
        assert result.modifier == 2

    def test_fudge_roll(self) -> None:
        result = roll_notation("fudge", rng=Random(42))
        assert result.dice_type == DiceType.FUDGE

    def test_advantage_forwarded(self) -> None:
        result = roll_notation("d20", advantage=True, rng=Random(42))
        assert result.advantage is True


# ===========================================================================
# Resolution Tests
# ===========================================================================


class TestDifficultyDC:
    def test_trivial_dc(self) -> None:
        assert DIFFICULTY_DC[DifficultyLevel.TRIVIAL] == 5

    def test_easy_dc(self) -> None:
        assert DIFFICULTY_DC[DifficultyLevel.EASY] == 10

    def test_moderate_dc(self) -> None:
        assert DIFFICULTY_DC[DifficultyLevel.MODERATE] == 15

    def test_hard_dc(self) -> None:
        assert DIFFICULTY_DC[DifficultyLevel.HARD] == 20

    def test_very_hard_dc(self) -> None:
        assert DIFFICULTY_DC[DifficultyLevel.VERY_HARD] == 25

    def test_legendary_dc(self) -> None:
        assert DIFFICULTY_DC[DifficultyLevel.LEGENDARY] == 30


class TestDetermineOutcome:
    def test_natural_20_crit_success(self) -> None:
        result = determine_outcome(total=20, dc=25, natural_roll=20, dice_type=DiceType.D20)
        assert result == OutcomeType.CRITICAL_SUCCESS

    def test_natural_1_crit_failure(self) -> None:
        result = determine_outcome(total=6, dc=5, natural_roll=1, dice_type=DiceType.D20)
        assert result == OutcomeType.CRITICAL_FAILURE

    def test_high_success(self) -> None:
        result = determine_outcome(total=20, dc=15)
        assert result == OutcomeType.SUCCESS

    def test_partial_success(self) -> None:
        result = determine_outcome(total=15, dc=15)
        assert result == OutcomeType.PARTIAL_SUCCESS

    def test_exact_dc_plus_5_is_success(self) -> None:
        result = determine_outcome(total=20, dc=15)
        assert result == OutcomeType.SUCCESS

    def test_failure(self) -> None:
        result = determine_outcome(total=13, dc=15)
        assert result == OutcomeType.FAILURE

    def test_critical_failure(self) -> None:
        result = determine_outcome(total=10, dc=15)
        assert result == OutcomeType.CRITICAL_FAILURE

    def test_non_d20_no_crit_override(self) -> None:
        """Non-D20 dice don't get natural crit detection — uses general thresholds."""
        # total=6, dc=10 → 6 < 10-3=7 → CRITICAL_FAILURE by threshold (not nat-1 override)
        result = determine_outcome(total=6, dc=10, natural_roll=6, dice_type=DiceType.D6)
        assert result == OutcomeType.CRITICAL_FAILURE
        # A D6 roll of 1 near the DC should NOT trigger nat-1 crit
        result2 = determine_outcome(total=8, dc=10, natural_roll=1, dice_type=DiceType.D6)
        assert result2 == OutcomeType.FAILURE  # 8 >= 10-3, so normal FAILURE


class TestResolveAction:
    def test_skill_check_moderate(self) -> None:
        result = resolve_action(
            ResolutionType.SKILL_CHECK,
            DifficultyLevel.MODERATE,
            rng=Random(42),
        )
        assert result.resolution_type == ResolutionType.SKILL_CHECK
        assert result.difficulty_check == 15
        assert isinstance(result.outcome, OutcomeType)

    def test_modifier_applied(self) -> None:
        result = resolve_action(
            ResolutionType.COMBAT_ACTION,
            DifficultyLevel.EASY,
            character_modifier=5,
            rng=Random(42),
        )
        assert result.dice_roll.modifier == 5
        assert result.character_modifier == 5

    def test_advantage_forwarded(self) -> None:
        result = resolve_action(
            ResolutionType.STEALTH_ACTION,
            DifficultyLevel.HARD,
            advantage=True,
            rng=Random(42),
        )
        assert result.dice_roll.advantage is True

    def test_success_margin_calculation(self) -> None:
        result = resolve_action(
            ResolutionType.SOCIAL_INTERACTION,
            DifficultyLevel.TRIVIAL,
            character_modifier=10,
            rng=Random(42),
        )
        expected_margin = result.dice_roll.total - 5
        assert result.success_margin == expected_margin

    def test_all_resolution_types(self) -> None:
        """All 13 resolution types can be resolved."""
        for rt in ResolutionType:
            result = resolve_action(rt, DifficultyLevel.MODERATE, rng=Random(42))
            assert result.resolution_type == rt


# ===========================================================================
# Character Stats Tests
# ===========================================================================


class TestStatType:
    def test_fourteen_stat_types(self) -> None:
        assert len(StatType) == 14

    def test_five_categories(self) -> None:
        assert len(StatCategory) == 5

    def test_all_stats_in_categories(self) -> None:
        all_stats: set[StatType] = set()
        for stats in STAT_CATEGORIES.values():
            all_stats.update(stats)
        assert all_stats == set(StatType)


class TestStatBlock:
    def test_default_modifier(self) -> None:
        """Default value (10) gives modifier 0."""
        block = StatBlock()
        assert block.modifier(StatType.STRENGTH) == 0

    def test_high_stat_modifier(self) -> None:
        block = StatBlock(values={"strength": 18})
        assert block.modifier(StatType.STRENGTH) == 4

    def test_low_stat_modifier(self) -> None:
        block = StatBlock(values={"strength": 6})
        assert block.modifier(StatType.STRENGTH) == -2

    def test_odd_stat_modifier(self) -> None:
        block = StatBlock(values={"dexterity": 15})
        assert block.modifier(StatType.DEXTERITY) == 2

    def test_with_update_immutable(self) -> None:
        """with_update returns a new instance, original unchanged."""
        original = StatBlock(values={"strength": 10})
        updated = original.with_update(StatType.STRENGTH, 18)
        assert original.values["strength"] == 10
        assert updated.values["strength"] == 18

    def test_with_update_clamps_max(self) -> None:
        block = StatBlock()
        updated = block.with_update(StatType.STRENGTH, 25)
        assert updated.values["strength"] == 20

    def test_with_update_clamps_min(self) -> None:
        block = StatBlock()
        updated = block.with_update(StatType.STRENGTH, -5)
        assert updated.values["strength"] == 1


class TestResolutionStatMap:
    def test_all_resolution_types_mapped(self) -> None:
        for rt in ResolutionType:
            assert rt in RESOLUTION_STAT_MAP

    def test_combat_uses_strength(self) -> None:
        assert RESOLUTION_STAT_MAP[ResolutionType.COMBAT_ACTION] == StatType.STRENGTH

    def test_stealth_uses_dexterity(self) -> None:
        assert RESOLUTION_STAT_MAP[ResolutionType.STEALTH_ACTION] == StatType.DEXTERITY


class TestStatProgression:
    def test_frozen(self) -> None:
        p = StatProgression(StatType.STRENGTH, 10, 14, "Training")
        assert p.stat_type == StatType.STRENGTH
        assert p.old_value == 10
        assert p.new_value == 14
        assert p.reason == "Training"


# ===========================================================================
# Stat Manager Tests
# ===========================================================================


class TestParseStatBlockContent:
    def test_parses_json_line(self) -> None:
        content = '[Character Stats] Carl\n\n{"strength": 14, "dexterity": 12}\n'
        result = _parse_stat_block_content(content)
        assert result == {"strength": 14, "dexterity": 12}

    def test_returns_none_for_no_json(self) -> None:
        assert _parse_stat_block_content("No JSON here") is None


class TestFormatStatBlockContent:
    def test_format_basic(self) -> None:
        block = StatBlock(values={"strength": 14})
        content = _format_stat_block_content("Carl", block)
        assert "[Character Stats] Carl" in content
        assert '"strength": 14' in content

    def test_format_with_progressions(self) -> None:
        block = StatBlock(values={"strength": 14})
        progs = [StatProgression(StatType.STRENGTH, 10, 14, "Training")]
        content = _format_stat_block_content("Carl", block, progs)
        assert "Progression:" in content
        assert "strength: 10 -> 14 (Training)" in content


class TestLoadStatBlock:
    def test_load_found(self) -> None:
        items = [
            FakeMemoryItem(
                "s1",
                '[Character Stats] Carl\n\n{"strength": 14, "dexterity": 12}\n',
                ["story", "character-stats"],
            )
        ]
        result = load_stat_block(_make_search(items), "Carl")
        assert result is not None
        assert result.values["strength"] == 14

    def test_load_not_found(self) -> None:
        result = load_stat_block(_make_search([]), "Unknown")
        assert result is None

    def test_load_ignores_wrong_character(self) -> None:
        items = [
            FakeMemoryItem(
                "s1",
                '[Character Stats] Karen\n\n{"charisma": 16}\n',
                ["story", "character-stats"],
            )
        ]
        result = load_stat_block(_make_search(items), "Carl")
        assert result is None


class TestSaveStatBlock:
    def test_save_returns_id(self) -> None:
        save_mock = _make_save()
        block = StatBlock(values={"strength": 14})
        result = save_stat_block(save_mock, "Carl", block)
        assert result == "saved-001"
        save_mock.assert_called_once()

    def test_save_content_format(self) -> None:
        save_mock = _make_save()
        block = StatBlock(values={"strength": 14})
        save_stat_block(save_mock, "Carl", block)
        call_kwargs = save_mock.call_args.kwargs
        assert "story" in call_kwargs["tags"]
        assert "character-stats" in call_kwargs["tags"]
        assert "[Character Stats] Carl" in call_kwargs["content"]


class TestGetStatModifierForResolution:
    def test_combat_strength_modifier(self) -> None:
        block = StatBlock(values={"strength": 18})
        mod = get_stat_modifier_for_resolution(block, ResolutionType.COMBAT_ACTION)
        assert mod == 4

    def test_default_modifier(self) -> None:
        block = StatBlock()
        mod = get_stat_modifier_for_resolution(block, ResolutionType.COMBAT_ACTION)
        assert mod == 0


# ===========================================================================
# Branching Tests
# ===========================================================================


class TestBranching:
    @pytest.mark.asyncio
    async def test_generate_branches_structure(self) -> None:
        from plugins.storytelling.application.branching import (
            BranchOptions,
            generate_branches,
        )

        branches_json = json.dumps(
            [
                {"description": "Branch 1 desc", "consequence_type": "success", "transition_hint": "Hint 1"},
                {"description": "Branch 2 desc", "consequence_type": "setback", "transition_hint": "Hint 2"},
                {"description": "Branch 3 desc", "consequence_type": "twist", "transition_hint": "Hint 3"},
            ]
        )

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=branches_json)

        result = ResolutionResult(
            resolution_type=ResolutionType.SKILL_CHECK,
            outcome=OutcomeType.SUCCESS,
            dice_roll=DiceRoll(DiceType.D20, (15,)),
            difficulty_check=15,
            success_margin=0,
        )
        options = await generate_branches(fake_llm, result)
        assert isinstance(options, BranchOptions)
        assert len(options.branches) == 3
        assert options.branches[0].description == "Branch 1 desc"

    @pytest.mark.asyncio
    async def test_generate_branches_handles_bad_json(self) -> None:
        from plugins.storytelling.application.branching import generate_branches

        async def bad_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="Not JSON at all")

        result = ResolutionResult(
            resolution_type=ResolutionType.SKILL_CHECK,
            outcome=OutcomeType.FAILURE,
            dice_roll=DiceRoll(DiceType.D20, (5,)),
            difficulty_check=15,
            success_margin=-10,
        )
        options = await generate_branches(bad_llm, result)
        assert options.branches == []

    @pytest.mark.asyncio
    async def test_generate_branches_handles_code_fence(self) -> None:
        from plugins.storytelling.application.branching import generate_branches

        branches_json = json.dumps(
            [
                {"description": "Fenced", "consequence_type": "ok", "transition_hint": "hint"},
            ]
        )

        async def fenced_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=f"```json\n{branches_json}\n```")

        result = ResolutionResult(
            resolution_type=ResolutionType.SKILL_CHECK,
            outcome=OutcomeType.SUCCESS,
            dice_roll=DiceRoll(DiceType.D20, (15,)),
            difficulty_check=15,
            success_margin=0,
        )
        options = await generate_branches(fenced_llm, result)
        assert len(options.branches) == 1

    def test_outcome_templates_cover_all_outcomes(self) -> None:
        from plugins.storytelling.application.branching import OUTCOME_TEMPLATES

        for outcome in OutcomeType:
            assert outcome in OUTCOME_TEMPLATES


# ===========================================================================
# Scene Integration Tests
# ===========================================================================


class TestSceneResolutionIntegration:
    @pytest.mark.asyncio
    async def test_resolution_context_in_prompt(self) -> None:
        """Resolution context appears in LLM system prompt."""
        from plugins.storytelling.application.scene_handler import generate_scene

        received_messages: list = []

        async def capturing_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            received_messages.append(messages)
            return FakeLLMResponse(content="Scene text")

        await generate_scene(
            memory_search=_make_search(),
            memory_save=_make_save(),
            llm_complete=capturing_llm,
            user_prompt="Test",
            resolution_context="The dice determined: SUCCESS. Margin: +3.",
        )
        system_msg = received_messages[0][0]["content"]
        assert "RESOLUTION OUTCOME" in system_msg
        assert "SUCCESS" in system_msg

    @pytest.mark.asyncio
    async def test_branch_context_in_prompt(self) -> None:
        """Branch context appears in LLM system prompt."""
        from plugins.storytelling.application.scene_handler import generate_scene

        received_messages: list = []

        async def capturing_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            received_messages.append(messages)
            return FakeLLMResponse(content="Scene text")

        await generate_scene(
            memory_search=_make_search(),
            memory_save=_make_save(),
            llm_complete=capturing_llm,
            user_prompt="Test",
            branch_context="Option A: Take the left path.",
        )
        system_msg = received_messages[0][0]["content"]
        assert "NARRATIVE OPTIONS" in system_msg
        assert "left path" in system_msg

    @pytest.mark.asyncio
    async def test_no_extra_sections_when_none(self) -> None:
        """No resolution/branch sections when not provided."""
        from plugins.storytelling.application.scene_handler import generate_scene

        received_messages: list = []

        async def capturing_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            received_messages.append(messages)
            return FakeLLMResponse(content="Scene text")

        await generate_scene(
            memory_search=_make_search(),
            memory_save=_make_save(),
            llm_complete=capturing_llm,
            user_prompt="Test",
        )
        system_msg = received_messages[0][0]["content"]
        assert "RESOLUTION OUTCOME" not in system_msg
        assert "NARRATIVE OPTIONS" not in system_msg


# ===========================================================================
# Handler Tests
# ===========================================================================


class TestStoryRollHandler:
    @pytest.mark.asyncio
    async def test_roll_handler_basic(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_roll_handler

        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={"notation": "d20"})
        result = await _story_roll_handler(task, {})
        assert result["dice_type"] == "d20"
        assert 1 <= result["total"] <= 20

    @pytest.mark.asyncio
    async def test_roll_handler_with_advantage(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_roll_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"notation": "d20", "advantage": True},
        )
        result = await _story_roll_handler(task, {})
        assert result["advantage"] is True

    @pytest.mark.asyncio
    async def test_roll_handler_notation(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_roll_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"notation": "3d6+2"},
        )
        result = await _story_roll_handler(task, {})
        assert result["dice_type"] == "d6"
        assert len(result["rolls"]) == 3
        assert result["modifier"] == 2


class TestStoryResolveHandler:
    @pytest.mark.asyncio
    async def test_resolve_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_resolve_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"resolution_type": "skill_check", "difficulty": "moderate"},
        )
        result = await _story_resolve_handler(task, {})
        assert result["resolution_type"] == "skill_check"
        assert result["difficulty_check"] == 15
        assert result["outcome"] in [o.value for o in OutcomeType]

    @pytest.mark.asyncio
    async def test_resolve_handler_invalid_type(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_resolve_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"resolution_type": "bogus", "difficulty": "moderate"},
        )
        with pytest.raises(ValueError, match="Invalid resolution type"):
            await _story_resolve_handler(task, {})

    @pytest.mark.asyncio
    async def test_resolve_handler_invalid_difficulty(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_resolve_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"resolution_type": "skill_check", "difficulty": "impossible"},
        )
        with pytest.raises(ValueError, match="Invalid difficulty"):
            await _story_resolve_handler(task, {})

    @pytest.mark.asyncio
    async def test_resolve_with_character_stats(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_resolve_handler

        stat_items = [
            FakeMemoryItem(
                "s1",
                '[Character Stats] Carl\n\n{"strength": 18, "dexterity": 14}\n',
                ["story", "character-stats"],
            )
        ]
        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={
                "resolution_type": "combat_action",
                "difficulty": "moderate",
                "character_name": "Carl",
            },
        )
        ctx = {"memory_search": _make_search(stat_items)}
        result = await _story_resolve_handler(task, ctx)
        assert result["character_modifier"] == 4  # (18 - 10) // 2


class TestStoryStatsHandlers:
    @pytest.mark.asyncio
    async def test_stats_get_found(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_stats_get_handler

        items = [
            FakeMemoryItem(
                "s1",
                '[Character Stats] Carl\n\n{"strength": 14}\n',
                ["story", "character-stats"],
            )
        ]
        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"character_name": "Carl"},
        )
        result = await _story_stats_get_handler(task, {"memory_search": _make_search(items)})
        assert result["found"] is True
        assert result["values"]["strength"] == 14

    @pytest.mark.asyncio
    async def test_stats_get_not_found(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_stats_get_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"character_name": "Unknown"},
        )
        result = await _story_stats_get_handler(task, {"memory_search": _make_search([])})
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_stats_get_requires_search(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_stats_get_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"character_name": "Carl"},
        )
        with pytest.raises(RuntimeError, match="memory_search"):
            await _story_stats_get_handler(task, {})

    @pytest.mark.asyncio
    async def test_stats_set_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_stats_set_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={
                "character_name": "Carl",
                "stat": "strength",
                "value": 16,
                "reason": "Training",
            },
        )
        ctx = {
            "memory_search": _make_search([]),
            "memory_save": _make_save(),
            "memory_update": MagicMock(),
        }
        result = await _story_stats_set_handler(task, ctx)
        assert result["character_name"] == "Carl"
        assert result["stat"] == "strength"

    @pytest.mark.asyncio
    async def test_stats_set_invalid_stat(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_stats_set_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"character_name": "Carl", "stat": "bogus", "value": 10},
        )
        ctx = {
            "memory_search": _make_search([]),
            "memory_save": _make_save(),
            "memory_update": MagicMock(),
        }
        with pytest.raises(ValueError, match="Invalid stat"):
            await _story_stats_set_handler(task, ctx)


# ===========================================================================
# Registration Tests
# ===========================================================================


class TestHandlerRegistration:
    def test_all_mechanics_handlers_registered(self) -> None:
        from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
        from plugins.storytelling.plugin import register

        handler_registry = TaskHandlerRegistry()
        plugin_registry = MagicMock()
        register(plugin_registry, handler_registry)

        for name in ("story.roll", "story.resolve", "story.stats.get", "story.stats.set", "story.branch"):
            assert handler_registry.get(name) is not None, f"Handler {name} not registered"


# ===========================================================================
# CLI Tests
# ===========================================================================


class TestMechanicsCLI:
    def test_roll_in_dispatch_table(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(
            story_command="roll",
            notation="d20",
            advantage=False,
            disadvantage=False,
        )
        container = MagicMock()
        with patch("builtins.print"):
            result = run(args, container)
        assert result == 0

    def test_roll_parser_registers(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "roll", "3d6+2", "--advantage"])
        assert args.story_command == "roll"
        assert args.notation == "3d6+2"
        assert args.advantage is True

    def test_resolve_parser_registers(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "resolve", "skill_check", "--difficulty", "moderate"])
        assert args.story_command == "resolve"
        assert args.resolution_type == "skill_check"
        assert args.difficulty == "moderate"

    def test_stats_parser_registers(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "stats", "Carl", "--project-id", "test-id"])
        assert args.story_command == "stats"
        assert args.character == "Carl"

    def test_stats_set_parser_registers(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(
            ["story", "stats-set", "Carl", "strength", "16", "--project-id", "test-id", "--reason", "Training"]
        )
        assert args.story_command == "stats-set"
        assert args.character == "Carl"
        assert args.stat == "strength"
        assert args.value == 16
        assert args.reason == "Training"

    def test_usage_includes_new_commands(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(story_command=None)
        container = MagicMock()
        with patch("builtins.print") as mock_print:
            result = run(args, container)
        assert result == 1
        printed = mock_print.call_args[0][0]
        assert "roll" in printed
        assert "resolve" in printed
        assert "stats" in printed
        assert "stats-set" in printed

    def test_roll_invalid_notation(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(
            story_command="roll",
            notation="xyz",
            advantage=False,
            disadvantage=False,
        )
        container = MagicMock()
        with patch("builtins.print"):
            result = run(args, container)
        assert result == 1

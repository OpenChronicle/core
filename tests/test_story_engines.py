"""Tests for narrative engines — consistency checker and emotional analyzer."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from plugins.storytelling.application.consistency_checker import (
    ConsistencyIssue,
    ConsistencyReport,
    _parse_consistency_response,
    check_consistency,
    validate_scene_consistency,
)
from plugins.storytelling.application.emotional_analyzer import (
    EmotionalBeat,
    EmotionalLoop,
    EmotionalReport,
    EmotionLabel,
    _parse_emotional_response,
    analyze_emotional_arc,
    detect_emotional_loops,
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
    created_at: str = ""


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
# Consistency Checker Tests
# ===========================================================================


class TestConsistencyIssue:
    def test_fields(self) -> None:
        issue = ConsistencyIssue(
            severity="error",
            description="Carl's eye color changed",
            entity_type="character",
            entity_name="Carl",
        )
        assert issue.severity == "error"
        assert issue.entity_name == "Carl"

    def test_defaults(self) -> None:
        issue = ConsistencyIssue(severity="info", description="Note", entity_type="", entity_name="")
        assert issue.conflicting_memories == []


class TestConsistencyReport:
    def test_defaults(self) -> None:
        report = ConsistencyReport()
        assert report.issues == []
        assert report.passed is True
        assert report.checked_items == 0


class TestParseConsistencyResponse:
    def test_parse_clean_json(self) -> None:
        response = json.dumps(
            {
                "issues": [
                    {
                        "severity": "error",
                        "description": "Eye color mismatch",
                        "entity_type": "character",
                        "entity_name": "Carl",
                    },
                    {
                        "severity": "warning",
                        "description": "Timeline gap",
                        "entity_type": "event",
                        "entity_name": "arrival",
                    },
                ],
                "summary": "Two issues found.",
            }
        )
        report = _parse_consistency_response(response, 10)
        assert len(report.issues) == 2
        assert report.issues[0].severity == "error"
        assert report.passed is False  # Has errors
        assert report.checked_items == 10

    def test_no_issues(self) -> None:
        response = json.dumps({"issues": [], "summary": "All clear."})
        report = _parse_consistency_response(response, 5)
        assert report.passed is True
        assert report.summary == "All clear."

    def test_warnings_only_passes(self) -> None:
        response = json.dumps(
            {
                "issues": [{"severity": "warning", "description": "Minor note", "entity_type": "", "entity_name": ""}],
                "summary": "Minor warning.",
            }
        )
        report = _parse_consistency_response(response, 3)
        assert report.passed is True  # Only warnings, no errors

    def test_bad_json(self) -> None:
        report = _parse_consistency_response("not json", 5)
        assert report.passed is True
        assert report.checked_items == 5

    def test_code_fenced_json(self) -> None:
        inner = json.dumps({"issues": [], "summary": "Clean."})
        response = f"```json\n{inner}\n```"
        report = _parse_consistency_response(response, 2)
        assert report.passed is True
        assert report.summary == "Clean."


class TestCheckConsistency:
    @pytest.mark.asyncio
    async def test_with_context(self) -> None:
        items = [
            FakeMemoryItem("c1", "Carl has blue eyes.", ["story", "character"]),
        ]

        response = json.dumps(
            {
                "issues": [
                    {
                        "severity": "error",
                        "description": "Eye color changed",
                        "entity_type": "character",
                        "entity_name": "Carl",
                    }
                ],
                "summary": "Contradiction found.",
            }
        )

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=response)

        report = await check_consistency(_make_search(items), fake_llm, "Carl's brown eyes gleamed.")
        assert not report.passed
        assert len(report.issues) == 1

    @pytest.mark.asyncio
    async def test_no_context(self) -> None:
        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="{}")

        report = await check_consistency(_make_search([]), fake_llm, "Some content")
        assert report.passed is True
        assert report.checked_items == 0

    @pytest.mark.asyncio
    async def test_validate_scene_convenience(self) -> None:
        items = [
            FakeMemoryItem("c1", "The lighthouse is tall.", ["story", "location"]),
        ]

        response = json.dumps({"issues": [], "summary": "Consistent."})

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=response)

        report = await validate_scene_consistency(_make_search(items), fake_llm, "The tall lighthouse loomed.")
        assert report.passed is True


# ===========================================================================
# Emotional Analyzer Tests
# ===========================================================================


class TestEmotionLabel:
    def test_nine_labels(self) -> None:
        assert len(EmotionLabel) == 9

    def test_values(self) -> None:
        assert EmotionLabel.JOY.value == "joy"
        assert EmotionLabel.NEUTRAL.value == "neutral"


class TestEmotionalBeat:
    def test_frozen(self) -> None:
        beat = EmotionalBeat(
            character_name="Carl",
            emotion=EmotionLabel.JOY,
            intensity=0.8,
            trigger="Reunion",
            scene_position="late",
        )
        assert beat.character_name == "Carl"
        assert beat.intensity == 0.8


class TestEmotionalLoop:
    def test_frozen(self) -> None:
        loop = EmotionalLoop(
            character_name="Carl",
            emotion=EmotionLabel.SADNESS,
            occurrence_count=4,
            confidence=0.8,
        )
        assert loop.occurrence_count == 4


class TestDetectEmotionalLoops:
    def test_no_loops_below_threshold(self) -> None:
        beats = [
            EmotionalBeat("Carl", EmotionLabel.JOY, 0.5, "event1", "early"),
            EmotionalBeat("Carl", EmotionLabel.SADNESS, 0.5, "event2", "middle"),
        ]
        loops = detect_emotional_loops(beats, [])
        assert loops == []

    def test_detects_loop(self) -> None:
        beats = [
            EmotionalBeat("Carl", EmotionLabel.ANGER, 0.5, "e1", "early"),
            EmotionalBeat("Carl", EmotionLabel.ANGER, 0.6, "e2", "middle"),
            EmotionalBeat("Carl", EmotionLabel.ANGER, 0.7, "e3", "late"),
        ]
        loops = detect_emotional_loops(beats, [])
        assert len(loops) == 1
        assert loops[0].character_name == "Carl"
        assert loops[0].emotion == EmotionLabel.ANGER
        assert loops[0].occurrence_count == 3

    def test_combines_current_and_prior(self) -> None:
        prior = [EmotionalBeat("Carl", EmotionLabel.FEAR, 0.5, "e1", "early")]
        current = [
            EmotionalBeat("Carl", EmotionLabel.FEAR, 0.6, "e2", "early"),
            EmotionalBeat("Carl", EmotionLabel.FEAR, 0.7, "e3", "middle"),
        ]
        loops = detect_emotional_loops(current, prior)
        assert len(loops) == 1
        assert loops[0].occurrence_count == 3

    def test_custom_threshold(self) -> None:
        beats = [
            EmotionalBeat("Carl", EmotionLabel.JOY, 0.5, "e1", "early"),
            EmotionalBeat("Carl", EmotionLabel.JOY, 0.5, "e2", "middle"),
        ]
        loops = detect_emotional_loops(beats, [], threshold=2)
        assert len(loops) == 1

    def test_per_character(self) -> None:
        beats = [
            EmotionalBeat("Carl", EmotionLabel.JOY, 0.5, "e1", "early"),
            EmotionalBeat("Karen", EmotionLabel.JOY, 0.5, "e2", "early"),
            EmotionalBeat("Carl", EmotionLabel.JOY, 0.5, "e3", "middle"),
            EmotionalBeat("Karen", EmotionLabel.JOY, 0.5, "e4", "middle"),
            EmotionalBeat("Carl", EmotionLabel.JOY, 0.5, "e5", "late"),
        ]
        loops = detect_emotional_loops(beats, [])
        # Carl has 3 joy, Karen has 2 joy — only Carl should trigger at threshold=3
        carl_loops = [lp for lp in loops if lp.character_name == "Carl"]
        karen_loops = [lp for lp in loops if lp.character_name == "Karen"]
        assert len(carl_loops) == 1
        assert len(karen_loops) == 0


class TestParseEmotionalResponse:
    def test_parse_clean_json(self) -> None:
        response = json.dumps(
            {
                "beats": [
                    {
                        "character_name": "Carl",
                        "emotion": "joy",
                        "intensity": 0.8,
                        "trigger": "Reunion",
                        "scene_position": "late",
                    },
                    {
                        "character_name": "Karen",
                        "emotion": "sadness",
                        "intensity": 0.5,
                        "trigger": "Memory",
                        "scene_position": "middle",
                    },
                ],
                "arc_summary": "Emotional contrast.",
            }
        )
        beats, summary = _parse_emotional_response(response)
        assert len(beats) == 2
        assert beats[0].emotion == EmotionLabel.JOY
        assert beats[0].intensity == 0.8
        assert summary == "Emotional contrast."

    def test_unknown_emotion_defaults_neutral(self) -> None:
        response = json.dumps(
            {
                "beats": [
                    {
                        "character_name": "X",
                        "emotion": "unknown",
                        "intensity": 0.5,
                        "trigger": "",
                        "scene_position": "early",
                    }
                ],
            }
        )
        beats, _ = _parse_emotional_response(response)
        assert beats[0].emotion == EmotionLabel.NEUTRAL

    def test_intensity_clamped(self) -> None:
        response = json.dumps(
            {
                "beats": [
                    {
                        "character_name": "X",
                        "emotion": "joy",
                        "intensity": 1.5,
                        "trigger": "",
                        "scene_position": "early",
                    }
                ],
            }
        )
        beats, _ = _parse_emotional_response(response)
        assert beats[0].intensity == 1.0

    def test_bad_json(self) -> None:
        beats, summary = _parse_emotional_response("not json")
        assert beats == []
        assert summary == ""


class TestAnalyzeEmotionalArc:
    @pytest.mark.asyncio
    async def test_basic_analysis(self) -> None:
        response = json.dumps(
            {
                "beats": [
                    {
                        "character_name": "Carl",
                        "emotion": "joy",
                        "intensity": 0.7,
                        "trigger": "Discovery",
                        "scene_position": "early",
                    },
                ],
                "arc_summary": "Carl is happy.",
            }
        )

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=response)

        report = await analyze_emotional_arc(_make_search([]), fake_llm, "Carl found the treasure.")
        assert isinstance(report, EmotionalReport)
        assert len(report.beats) == 1
        assert report.arc_summary == "Carl is happy."
        assert "Carl" in report.character_arcs

    @pytest.mark.asyncio
    async def test_with_character_names(self) -> None:
        response = json.dumps({"beats": [], "arc_summary": "Focused analysis."})

        received_prompts: list[str] = []

        async def capturing_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            received_prompts.append(messages[1]["content"])
            return FakeLLMResponse(content=response)

        await analyze_emotional_arc(
            _make_search([]),
            capturing_llm,
            "Scene text",
            character_names=["Carl", "Karen"],
        )
        assert "Carl, Karen" in received_prompts[0]


# ===========================================================================
# Scene Integration Tests
# ===========================================================================


class TestSceneEngineIntegration:
    @pytest.mark.asyncio
    async def test_consistency_flag(self) -> None:
        """Scene with validate_consistency=True runs the checker."""
        from plugins.storytelling.application.scene_handler import generate_scene

        # Provide story context so the checker actually calls the LLM
        context_items = [
            FakeMemoryItem("c1", "Carl has blue eyes.", ["story", "character"]),
        ]

        call_count = 0

        async def counting_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FakeLLMResponse(content="Generated scene.")
            # Second call is consistency check
            return FakeLLMResponse(content=json.dumps({"issues": [], "summary": "OK"}))

        result = await generate_scene(
            memory_search=_make_search(context_items),
            memory_save=_make_save(),
            llm_complete=counting_llm,
            user_prompt="Test",
            validate_consistency=True,
        )
        assert result.consistency_report is not None
        assert result.consistency_report.passed is True
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_emotion_flag(self) -> None:
        """Scene with analyze_emotion=True runs the analyzer."""
        from plugins.storytelling.application.scene_handler import generate_scene

        call_count = 0

        async def counting_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return FakeLLMResponse(content="Generated scene.")
            return FakeLLMResponse(content=json.dumps({"beats": [], "arc_summary": "Flat"}))

        result = await generate_scene(
            memory_search=_make_search(),
            memory_save=_make_save(),
            llm_complete=counting_llm,
            user_prompt="Test",
            analyze_emotion=True,
        )
        assert result.emotional_report is not None
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_analysis_by_default(self) -> None:
        from plugins.storytelling.application.scene_handler import generate_scene

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="Scene.")

        result = await generate_scene(
            memory_search=_make_search(),
            memory_save=_make_save(),
            llm_complete=fake_llm,
            user_prompt="Test",
        )
        assert result.consistency_report is None
        assert result.emotional_report is None


# ===========================================================================
# Handler Tests
# ===========================================================================


class TestNarrativeEngineHandlers:
    @pytest.mark.asyncio
    async def test_consistency_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_consistency_check_handler

        response = json.dumps({"issues": [], "summary": "OK"})

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=response)

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"content": "Test scene text"},
        )
        ctx = {"memory_search": _make_search([]), "llm_complete": fake_llm}
        result = await _story_consistency_check_handler(task, ctx)
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_consistency_handler_requires_content(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_consistency_check_handler

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="{}")

        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={})
        with pytest.raises(ValueError, match="content is required"):
            await _story_consistency_check_handler(task, {"memory_search": _make_search([]), "llm_complete": fake_llm})

    @pytest.mark.asyncio
    async def test_emotion_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_emotion_analyze_handler

        response = json.dumps(
            {
                "beats": [
                    {
                        "character_name": "Carl",
                        "emotion": "joy",
                        "intensity": 0.8,
                        "trigger": "Win",
                        "scene_position": "late",
                    }
                ],
                "arc_summary": "Joyful.",
            }
        )

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=response)

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"scene_text": "Carl wins."},
        )
        ctx = {"memory_search": _make_search([]), "llm_complete": fake_llm}
        result = await _story_emotion_analyze_handler(task, ctx)
        assert result["arc_summary"] == "Joyful."
        assert len(result["beats"]) == 1

    @pytest.mark.asyncio
    async def test_emotion_handler_requires_text(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_emotion_analyze_handler

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="{}")

        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={})
        with pytest.raises(ValueError, match="scene_text is required"):
            await _story_emotion_analyze_handler(task, {"memory_search": _make_search([]), "llm_complete": fake_llm})


class TestNarrativeEngineRegistration:
    def test_handlers_registered(self) -> None:
        from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
        from plugins.storytelling.plugin import register

        handler_registry = TaskHandlerRegistry()
        plugin_registry = MagicMock()
        register(plugin_registry, handler_registry)

        for name in ("story.consistency.check", "story.emotion.analyze"):
            assert handler_registry.get(name) is not None, f"Handler {name} not registered"


# ===========================================================================
# CLI Tests
# ===========================================================================


class TestNarrativeEngineCLI:
    def test_consistency_in_dispatch(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(
            story_command="consistency",
            content=["test text"],
            project_id="test-id",
        )
        container = MagicMock()
        container.storage.get_project.return_value = None
        with patch("builtins.print"):
            result = run(args, container)
        assert result == 1  # Project not found, but dispatch worked

    def test_emotion_in_dispatch(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(
            story_command="emotion",
            content=["test text"],
            project_id="test-id",
            characters=None,
        )
        container = MagicMock()
        container.storage.get_project.return_value = None
        with patch("builtins.print"):
            result = run(args, container)
        assert result == 1

    def test_consistency_parser(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "consistency", "test", "content", "--project-id", "test-id"])
        assert args.story_command == "consistency"
        assert args.content == ["test", "content"]

    def test_emotion_parser(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(
            ["story", "emotion", "scene", "text", "--project-id", "test-id", "--characters", "Carl,Karen"]
        )
        assert args.story_command == "emotion"
        assert args.characters == "Carl,Karen"

    def test_scene_consistency_flag(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "scene", "--project-id", "t", "--check-consistency", "prompt"])
        assert args.check_consistency is True

    def test_scene_emotion_flag(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "scene", "--project-id", "t", "--analyze-emotion", "prompt"])
        assert args.analyze_emotion is True

    def test_usage_includes_engines(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(story_command=None)
        container = MagicMock()
        with patch("builtins.print") as mock_print:
            run(args, container)
        printed = mock_print.call_args[0][0]
        assert "consistency" in printed
        assert "emotion" in printed

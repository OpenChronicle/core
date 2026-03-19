"""Tests for persona extractor stub."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from plugins.storytelling.application.persona_extractor import (
    _format_persona_content,
    _parse_persona_response,
    extract_persona,
    extract_persona_from_text,
)
from plugins.storytelling.domain.persona import (
    ExtractedPersona,
    PersonaExtractionStatus,
    PersonaSource,
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
    mock.return_value = FakeMemoryItem(id="saved-persona-001", content="", tags=[])
    return mock


# ===========================================================================
# Domain Model Tests
# ===========================================================================


class TestPersonaSource:
    def test_text_source(self) -> None:
        src = PersonaSource(source_type="text", content_ref="Character description text")
        assert src.source_type == "text"

    def test_image_source(self) -> None:
        src = PersonaSource(source_type="image", content_ref="asset-123")
        assert src.source_type == "image"


class TestExtractedPersona:
    def test_defaults(self) -> None:
        persona = ExtractedPersona(character_name="Carl")
        assert persona.physical_description == ""
        assert persona.confidence == 0.0

    def test_frozen(self) -> None:
        persona = ExtractedPersona(
            character_name="Carl",
            physical_description="Tall, lean",
            confidence=0.85,
        )
        assert persona.character_name == "Carl"
        assert persona.confidence == 0.85


class TestPersonaExtractionStatus:
    def test_all_statuses(self) -> None:
        assert len(PersonaExtractionStatus) == 5

    def test_values(self) -> None:
        assert PersonaExtractionStatus.NOT_AVAILABLE.value == "not_available"
        assert PersonaExtractionStatus.READY.value == "ready"
        assert PersonaExtractionStatus.COMPLETED.value == "completed"


# ===========================================================================
# Extractor Tests
# ===========================================================================


class TestExtractPersona:
    @pytest.mark.asyncio
    async def test_non_text_source_rejected(self) -> None:
        sources = [PersonaSource(source_type="image", content_ref="img-001")]

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="{}")

        result = await extract_persona(_make_search(), _make_save(), fake_llm, "Carl", sources)
        assert result["status"] == "not_available"
        assert "unsupported_sources" in result

    @pytest.mark.asyncio
    async def test_text_extraction_succeeds(self) -> None:
        persona_json = json.dumps(
            {
                "physical_description": "Tall with glasses",
                "voice_description": "Deep baritone",
                "mannerisms": "Paces when thinking",
                "personality_traits": "Analytical, stubborn",
                "confidence": 0.85,
            }
        )

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=persona_json)

        sources = [PersonaSource(source_type="text", content_ref="Carl is tall, wears glasses.")]
        save_mock = _make_save()
        result = await extract_persona(_make_search(), save_mock, fake_llm, "Carl", sources)
        assert result["status"] == "completed"
        assert result["character_name"] == "Carl"
        assert result["confidence"] == 0.85
        save_mock.assert_called_once()


class TestExtractPersonaFromText:
    @pytest.mark.asyncio
    async def test_basic_extraction(self) -> None:
        persona_json = json.dumps(
            {
                "physical_description": "Short hair",
                "voice_description": "Soft spoken",
                "mannerisms": "Taps foot",
                "personality_traits": "Kind",
                "confidence": 0.7,
            }
        )

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=persona_json)

        persona = await extract_persona_from_text(fake_llm, "Karen", "Karen is kind.")
        assert persona.character_name == "Karen"
        assert persona.confidence == 0.7


class TestParsePersonaResponse:
    def test_valid_json(self) -> None:
        content = json.dumps(
            {
                "physical_description": "Tall",
                "confidence": 0.9,
            }
        )
        persona = _parse_persona_response("Carl", content)
        assert persona.physical_description == "Tall"
        assert persona.confidence == 0.9

    def test_bad_json_returns_empty(self) -> None:
        persona = _parse_persona_response("Carl", "not json")
        assert persona.character_name == "Carl"
        assert persona.confidence == 0.0

    def test_confidence_clamped(self) -> None:
        content = json.dumps({"confidence": 1.5})
        persona = _parse_persona_response("Carl", content)
        assert persona.confidence == 1.0


class TestFormatPersonaContent:
    def test_format(self) -> None:
        persona = ExtractedPersona(
            character_name="Carl",
            physical_description="Tall",
            voice_description="Deep",
            confidence=0.85,
        )
        content = _format_persona_content(persona)
        assert "[Persona] Carl" in content
        assert "0.85" in content
        assert "Tall" in content
        assert "Deep" in content


# ===========================================================================
# Handler Tests
# ===========================================================================


class TestPersonaHandlers:
    @pytest.mark.asyncio
    async def test_extract_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_persona_extract_handler

        persona_json = json.dumps(
            {
                "physical_description": "Lean build",
                "confidence": 0.8,
            }
        )

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content=persona_json)

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"character_name": "Carl", "source_text": "Carl is lean."},
        )
        ctx = {
            "memory_search": _make_search([]),
            "memory_save": _make_save(),
            "llm_complete": fake_llm,
        }
        result = await _story_persona_extract_handler(task, ctx)
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_status_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_persona_status_handler

        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={})
        result = await _story_persona_status_handler(task, {})
        assert result["text_extraction"] == "ready"
        assert result["image_extraction"] == "not_available"

    @pytest.mark.asyncio
    async def test_extract_requires_name(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_persona_extract_handler

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="{}")

        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={"source_text": "text"})
        ctx = {"memory_search": _make_search([]), "memory_save": _make_save(), "llm_complete": fake_llm}
        with pytest.raises(ValueError, match="character_name is required"):
            await _story_persona_extract_handler(task, ctx)


class TestPersonaRegistration:
    def test_handlers_registered(self) -> None:
        from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
        from plugins.storytelling.plugin import register

        handler_registry = TaskHandlerRegistry()
        plugin_registry = MagicMock()
        register(plugin_registry, handler_registry)

        for name in ("story.persona.extract", "story.persona.status"):
            assert handler_registry.get(name) is not None, f"Handler {name} not registered"


# ===========================================================================
# CLI Tests
# ===========================================================================


class TestPersonaCLI:
    def test_persona_in_dispatch(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(story_command="persona", persona_command=None)
        container = MagicMock()
        with patch("builtins.print"):
            result = run(args, container)
        assert result == 1

    def test_persona_status_cli(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(story_command="persona", persona_command="status")
        container = MagicMock()
        with patch("builtins.print"):
            result = run(args, container)
        assert result == 0

    def test_persona_parser(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(
            ["story", "persona", "extract", "Carl", "--project-id", "test-id", "--source-text", "Carl is tall."]
        )
        assert args.persona_command == "extract"
        assert args.name == "Carl"
        assert args.source_text == "Carl is tall."

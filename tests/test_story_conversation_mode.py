"""Tests for storytelling conversation mode integration (Phase 3).

Covers:
- Mode prompt builder registry (PluginRegistry port + InMemoryPluginRegistry)
- prepare_ask integration with mode_prompt_builders
- make_memory_search_closure extraction
- story_prompt_builder plugin function
- Plugin registration wiring
- CLI convenience commands (characters, locations, search)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from openchronicle.core.application.runtime.plugin_loader import InMemoryPluginRegistry
from openchronicle.core.domain.models.memory_item import MemoryItem

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeMemoryItem:
    """Minimal stand-in for MemoryItem in tests."""

    id: str
    content: str
    tags: list[str]
    pinned: bool = False


def _make_search(items: list[FakeMemoryItem]) -> Any:
    """Create a mock memory_search that filters by tags."""

    def search(query: str, top_k: int = 8, tags: list[str] | None = None) -> list[FakeMemoryItem]:
        results = items
        if tags:
            results = [i for i in results if all(t in i.tags for t in tags)]
        return results[:top_k]

    return search


def _sample_memory(**overrides: Any) -> MemoryItem:
    from openchronicle.core.domain.time_utils import utc_now

    defaults: dict[str, Any] = {
        "id": "mem-1",
        "content": "Test memory",
        "tags": [],
        "pinned": False,
        "project_id": None,
        "source": "test",
        "created_at": utc_now(),
    }
    defaults.update(overrides)
    return MemoryItem(**defaults)


def _sample_conversation(**overrides: Any) -> Any:
    defaults = {
        "id": "convo-1",
        "title": "Test Conversation",
        "project_id": "proj-1",
        "mode": "general",
        "created_at": __import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").UTC),
    }
    defaults.update(overrides)
    convo = MagicMock()
    for k, v in defaults.items():
        setattr(convo, k, v)
    return convo


def _mock_router() -> MagicMock:
    router = MagicMock()
    hint = MagicMock()
    hint.mode_hint = "general"
    hint.nsfw_score = 0.0
    hint.requires_nsfw_capable_model = False
    hint.reason_codes = []
    router.analyze.return_value = hint
    return router


def _mock_router_policy() -> MagicMock:
    policy = MagicMock()
    route = MagicMock()
    route.provider = "stub"
    route.model = "stub-model"
    route.mode = "fast"
    route.reasons = ["default"]
    route.predictor_hint = None
    route.predictor_source = None
    policy.route.return_value = route
    return policy


# ---------------------------------------------------------------------------
# Mode Builder Registry Tests
# ---------------------------------------------------------------------------


class TestModeBuilderRegistry:
    """Tests for the ModePromptBuilder registration on PluginRegistry."""

    def test_register_and_retrieve_builder(self) -> None:
        registry = InMemoryPluginRegistry()

        def my_builder(prompt_text: str, *, memory_search: Any, project_id: str | None = None) -> str:
            return "custom prompt"

        registry.register_mode_prompt_builder("story", my_builder)
        assert registry.get_mode_prompt_builder("story") is my_builder

    def test_returns_none_for_unknown_mode(self) -> None:
        registry = InMemoryPluginRegistry()
        assert registry.get_mode_prompt_builder("unknown") is None

    def test_mode_prompt_builders_returns_full_dict(self) -> None:
        registry = InMemoryPluginRegistry()

        def builder_a(prompt_text: str, *, memory_search: Any, project_id: str | None = None) -> str:
            return "a"

        def builder_b(prompt_text: str, *, memory_search: Any, project_id: str | None = None) -> str:
            return "b"

        registry.register_mode_prompt_builder("story", builder_a)
        registry.register_mode_prompt_builder("persona", builder_b)

        builders = registry.mode_prompt_builders()
        assert len(builders) == 2
        assert builders["story"] is builder_a
        assert builders["persona"] is builder_b

    def test_mode_prompt_builders_returns_copy(self) -> None:
        """Returned dict is a copy — mutations don't affect the registry."""
        registry = InMemoryPluginRegistry()

        def builder(prompt_text: str, *, memory_search: Any, project_id: str | None = None) -> str:
            return "x"

        registry.register_mode_prompt_builder("story", builder)
        copy = registry.mode_prompt_builders()
        copy["hacked"] = builder
        assert registry.get_mode_prompt_builder("hacked") is None


# ---------------------------------------------------------------------------
# prepare_ask Integration Tests
# ---------------------------------------------------------------------------


def _build_stores(
    *,
    conversation_mode: str = "general",
    memories: list[MemoryItem] | None = None,
    project_id: str | None = "proj-1",
) -> tuple[MagicMock, MagicMock]:
    convo_store = MagicMock()
    convo_store.get_conversation.return_value = _sample_conversation(mode=conversation_mode, project_id=project_id)
    convo_store.list_turns.return_value = []

    memory_store = MagicMock()
    memory_store.list_memory.return_value = memories or []
    memory_store.search_memory.return_value = memories or [_sample_memory()]
    return convo_store, memory_store


class TestPrepareAskModeBuilders:
    """Tests for mode_prompt_builders parameter in prepare_ask."""

    @pytest.mark.asyncio
    async def test_story_mode_with_builder_uses_custom_prompt(self) -> None:
        """When mode=story and a builder is registered, system prompt comes from builder."""
        from openchronicle.core.application.use_cases.ask_conversation import prepare_ask

        convo_store, memory_store = _build_stores(conversation_mode="story")

        def story_builder(prompt_text: str, *, memory_search: Any, project_id: str | None = None) -> str:
            return "You are a storytelling assistant."

        ctx = await prepare_ask(
            convo_store=convo_store,
            memory_store=memory_store,
            emit_event=lambda e: None,
            conversation_id="convo-1",
            prompt_text="Tell me a story",
            interaction_router=_mock_router(),
            router_policy=_mock_router_policy(),
            mode_prompt_builders={"story": story_builder},
        )

        assert ctx.messages[0]["role"] == "system"
        assert ctx.messages[0]["content"] == "You are a storytelling assistant."

    @pytest.mark.asyncio
    async def test_story_mode_with_builder_skips_generic_memory_retrieval(self) -> None:
        """When a builder is active, generic search_memory is not called."""
        from openchronicle.core.application.use_cases.ask_conversation import prepare_ask

        convo_store, memory_store = _build_stores(conversation_mode="story")

        def story_builder(prompt_text: str, *, memory_search: Any, project_id: str | None = None) -> str:
            return "Story prompt"

        await prepare_ask(
            convo_store=convo_store,
            memory_store=memory_store,
            emit_event=lambda e: None,
            conversation_id="convo-1",
            prompt_text="test",
            interaction_router=_mock_router(),
            router_policy=_mock_router_policy(),
            mode_prompt_builders={"story": story_builder},
        )

        # search_memory should NOT be called (builder does its own retrieval)
        memory_store.search_memory.assert_not_called()

    @pytest.mark.asyncio
    async def test_story_mode_with_builder_still_includes_pinned(self) -> None:
        """Pinned memories are still retrieved even when a builder is active."""
        from openchronicle.core.application.use_cases.ask_conversation import prepare_ask

        pinned = [_sample_memory(id="pinned-1", content="Standing rule", pinned=True)]
        convo_store, memory_store = _build_stores(conversation_mode="story", memories=pinned)

        def story_builder(prompt_text: str, *, memory_search: Any, project_id: str | None = None) -> str:
            return "Story prompt"

        ctx = await prepare_ask(
            convo_store=convo_store,
            memory_store=memory_store,
            emit_event=lambda e: None,
            conversation_id="convo-1",
            prompt_text="test",
            interaction_router=_mock_router(),
            router_policy=_mock_router_policy(),
            include_pinned_memory=True,
            mode_prompt_builders={"story": story_builder},
        )

        # list_memory(pinned_only=True) should still be called
        memory_store.list_memory.assert_called_once_with(pinned_only=True)
        # retrieved_ids should include pinned IDs
        assert "pinned-1" in ctx.retrieved_ids

    @pytest.mark.asyncio
    async def test_general_mode_ignores_registered_builders(self) -> None:
        """When mode=general, registered builders have no effect."""
        from openchronicle.core.application.use_cases.ask_conversation import prepare_ask

        convo_store, memory_store = _build_stores(conversation_mode="general")

        def story_builder(prompt_text: str, *, memory_search: Any, project_id: str | None = None) -> str:
            return "Should not appear"

        ctx = await prepare_ask(
            convo_store=convo_store,
            memory_store=memory_store,
            emit_event=lambda e: None,
            conversation_id="convo-1",
            prompt_text="hello",
            interaction_router=_mock_router(),
            router_policy=_mock_router_policy(),
            mode_prompt_builders={"story": story_builder},
        )

        assert ctx.messages[0]["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_no_builders_dict_uses_default_prompt(self) -> None:
        """When mode_prompt_builders is None, default prompt is used regardless of mode."""
        from openchronicle.core.application.use_cases.ask_conversation import prepare_ask

        convo_store, memory_store = _build_stores(conversation_mode="story")

        ctx = await prepare_ask(
            convo_store=convo_store,
            memory_store=memory_store,
            emit_event=lambda e: None,
            conversation_id="convo-1",
            prompt_text="test",
            interaction_router=_mock_router(),
            router_policy=_mock_router_policy(),
            mode_prompt_builders=None,
        )

        assert ctx.messages[0]["content"] == "You are a helpful assistant."


# ---------------------------------------------------------------------------
# make_memory_search_closure Tests
# ---------------------------------------------------------------------------


class TestMakeMemorySearchClosure:
    """Tests for the extracted make_memory_search_closure utility."""

    def test_closure_routes_through_search_memory_use_case(self) -> None:
        from openchronicle.core.application.services.context_builder import make_memory_search_closure

        memory_store = MagicMock()
        expected = [_sample_memory()]
        memory_store.search_memory.return_value = expected

        with patch(
            "openchronicle.core.application.use_cases.search_memory.execute",
            return_value=expected,
        ) as mock_exec:
            search = make_memory_search_closure(memory_store, "proj-1")
            result = search("test query", top_k=5, tags=["story"])

        mock_exec.assert_called_once_with(
            memory_store,
            "test query",
            top_k=5,
            project_id="proj-1",
            tags=["story"],
            embedding_service=None,
        )
        assert result == expected

    def test_closure_passes_embedding_service(self) -> None:
        from openchronicle.core.application.services.context_builder import make_memory_search_closure

        memory_store = MagicMock()
        embedding_svc = MagicMock()

        with patch(
            "openchronicle.core.application.use_cases.search_memory.execute",
            return_value=[],
        ) as mock_exec:
            search = make_memory_search_closure(memory_store, "proj-1", embedding_svc)
            search("query")

        _, kwargs = mock_exec.call_args
        assert kwargs["embedding_service"] is embedding_svc


# ---------------------------------------------------------------------------
# Plugin — story_prompt_builder Tests
# ---------------------------------------------------------------------------


class TestStoryPromptBuilder:
    """Tests for the story mode prompt builder function."""

    def test_calls_assemble_and_returns_prompt(self) -> None:
        from plugins.storytelling.application.conversation_mode import story_prompt_builder

        items = [
            FakeMemoryItem("i1", "Follow the guide.", ["story", "instructions"]),
            FakeMemoryItem("c1", "Carl is 42.", ["story", "character"]),
        ]
        result = story_prompt_builder("Tell me about Carl", memory_search=_make_search(items))
        # Should contain mode directive (director mode)
        assert "DIRECTOR" in result.upper() or "director" in result.lower() or "direct the narrative" in result.lower()
        # Should contain the canon directive
        assert "canon" in result.lower()

    def test_defaults_to_director_mode(self) -> None:
        from plugins.storytelling.application.conversation_mode import story_prompt_builder

        result = story_prompt_builder("test", memory_search=_make_search([]))
        # Director mode directive should be present even with empty content
        assert "director" in result.lower() or "DIRECTOR" in result.upper()

    def test_handles_empty_story_context_gracefully(self) -> None:
        from plugins.storytelling.application.conversation_mode import story_prompt_builder

        result = story_prompt_builder("test", memory_search=_make_search([]))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_passes_project_id_to_builder(self) -> None:
        """project_id is accepted but doesn't change behavior (used for future extensibility)."""
        from plugins.storytelling.application.conversation_mode import story_prompt_builder

        result = story_prompt_builder("test", memory_search=_make_search([]), project_id="proj-123")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Plugin Registration Test
# ---------------------------------------------------------------------------


class TestStoryPluginRegistration:
    """Test that register() wires the mode builder correctly."""

    def test_register_wires_mode_builder(self) -> None:
        from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry

        registry = InMemoryPluginRegistry()
        handler_registry = TaskHandlerRegistry()

        from plugins.storytelling.plugin import register

        register(registry, handler_registry)

        builder = registry.get_mode_prompt_builder("story")
        assert builder is not None
        assert callable(builder)


# ---------------------------------------------------------------------------
# CLI Convenience Command Tests
# ---------------------------------------------------------------------------


class TestStoryCLICharacters:
    """Tests for oc story characters subcommand."""

    def test_characters_dispatches_with_tag_filter(self) -> None:
        from plugins.storytelling.cli import _cmd_story_characters

        container = MagicMock()
        items = [_sample_memory(id="c1", content="[Character] Carl\nAge: 42", tags=["story", "character"])]
        container.storage.search_memory.return_value = items

        args = argparse.Namespace(project_id="proj-1", primary_only=False)
        result = _cmd_story_characters(args, container)

        assert result == 0
        container.storage.search_memory.assert_called_once_with(
            "character", project_id="proj-1", top_k=200, tags=["story", "character"]
        )

    def test_characters_primary_only_filter(self) -> None:
        from plugins.storytelling.cli import _cmd_story_characters

        container = MagicMock()
        container.storage.search_memory.return_value = []

        args = argparse.Namespace(project_id="proj-1", primary_only=True)
        _cmd_story_characters(args, container)

        container.storage.search_memory.assert_called_once_with(
            "character", project_id="proj-1", top_k=200, tags=["story", "character", "primary"]
        )


class TestStoryCLILocations:
    """Tests for oc story locations subcommand."""

    def test_locations_dispatches_with_tag_filter(self) -> None:
        from plugins.storytelling.cli import _cmd_story_locations

        container = MagicMock()
        items = [_sample_memory(id="l1", content="[Location] Lighthouse", tags=["story", "location"])]
        container.storage.search_memory.return_value = items

        args = argparse.Namespace(project_id="proj-1")
        result = _cmd_story_locations(args, container)

        assert result == 0
        container.storage.search_memory.assert_called_once_with(
            "location", project_id="proj-1", top_k=200, tags=["story", "location"]
        )


class TestStoryCLISearch:
    """Tests for oc story search subcommand."""

    def test_search_dispatches_with_query_and_story_tag(self) -> None:
        from plugins.storytelling.cli import _cmd_story_search

        container = MagicMock()
        items = [_sample_memory(id="r1", content="Carl explores", tags=["story", "scene"])]
        container.storage.search_memory.return_value = items

        args = argparse.Namespace(project_id="proj-1", query=["Carl", "lighthouse"])
        result = _cmd_story_search(args, container)

        assert result == 0
        container.storage.search_memory.assert_called_once_with(
            "Carl lighthouse", project_id="proj-1", top_k=20, tags=["story"]
        )

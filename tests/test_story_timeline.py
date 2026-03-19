"""Tests for storytelling bookmarks and timeline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from plugins.storytelling.application.bookmark_manager import (
    _format_bookmark_content,
    _parse_bookmark,
    create_bookmark,
    delete_bookmark,
    list_bookmarks,
)
from plugins.storytelling.application.timeline_assembler import (
    assemble_timeline,
    get_chapter_list,
)
from plugins.storytelling.domain.timeline import (
    Bookmark,
    BookmarkType,
    Timeline,
    TimelineEntry,
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
    mock.return_value = FakeMemoryItem(id="saved-bm-001", content="", tags=[], created_at="2026-01-01T00:00:00")
    return mock


# ===========================================================================
# Domain Model Tests
# ===========================================================================


class TestBookmarkType:
    def test_four_types(self) -> None:
        assert len(BookmarkType) == 4

    def test_values(self) -> None:
        assert BookmarkType.USER.value == "user"
        assert BookmarkType.AUTO.value == "auto"
        assert BookmarkType.MILESTONE.value == "milestone"
        assert BookmarkType.CHAPTER.value == "chapter"


class TestBookmark:
    def test_frozen(self) -> None:
        bm = Bookmark(id="b1", scene_id="s1", label="Test", bookmark_type=BookmarkType.USER)
        assert bm.id == "b1"
        assert bm.scene_id == "s1"
        assert bm.label == "Test"

    def test_defaults(self) -> None:
        bm = Bookmark(id="b1", scene_id=None, label="Test", bookmark_type=BookmarkType.USER)
        assert bm.chapter is None
        assert bm.position == 0
        assert bm.created_at == ""


class TestTimelineEntry:
    def test_scene_entry(self) -> None:
        e = TimelineEntry(memory_id="m1", entry_type="scene", label="Scene 1")
        assert e.entry_type == "scene"

    def test_bookmark_entry(self) -> None:
        e = TimelineEntry(memory_id="m2", entry_type="bookmark", label="Bookmark 1", chapter="Act One")
        assert e.chapter == "Act One"


class TestTimeline:
    def test_empty_timeline(self) -> None:
        t = Timeline()
        assert t.entries == []
        assert t.chapters == {}


# ===========================================================================
# Bookmark Manager Tests
# ===========================================================================


class TestFormatBookmarkContent:
    def test_basic_format(self) -> None:
        content = _format_bookmark_content("Test Bookmark", BookmarkType.USER)
        assert "[Bookmark] Test Bookmark" in content
        assert "Type: user" in content

    def test_with_scene_id(self) -> None:
        content = _format_bookmark_content("Test", BookmarkType.AUTO, scene_id="scene-123")
        assert "Scene: scene-123" in content

    def test_with_chapter(self) -> None:
        content = _format_bookmark_content("Test", BookmarkType.CHAPTER, chapter="Act One")
        assert "Chapter: Act One" in content


class TestParseBookmark:
    def test_parse_basic(self) -> None:
        content = "[Bookmark] Carl's Arrival\nType: user | Chapter: Act One | Position: 3\nScene: scene-001"
        bm = _parse_bookmark("bm1", content, ["story", "bookmark", "user"])
        assert bm is not None
        assert bm.label == "Carl's Arrival"
        assert bm.bookmark_type == BookmarkType.USER
        assert bm.chapter == "Act One"
        assert bm.position == 3
        assert bm.scene_id == "scene-001"

    def test_parse_no_chapter(self) -> None:
        content = "[Bookmark] Test\nType: auto | Chapter: None | Position: 0"
        bm = _parse_bookmark("bm2", content, ["story", "bookmark"])
        assert bm is not None
        assert bm.chapter is None

    def test_parse_non_bookmark(self) -> None:
        bm = _parse_bookmark("x", "Not a bookmark", [])
        assert bm is None

    def test_roundtrip(self) -> None:
        content = _format_bookmark_content("Test", BookmarkType.MILESTONE, scene_id="s1", chapter="Ch1", position=5)
        bm = _parse_bookmark("id1", content, ["story", "bookmark"])
        assert bm is not None
        assert bm.label == "Test"
        assert bm.bookmark_type == BookmarkType.MILESTONE
        assert bm.scene_id == "s1"
        assert bm.chapter == "Ch1"
        assert bm.position == 5


class TestCreateBookmark:
    def test_creates_and_returns(self) -> None:
        save_mock = _make_save()
        bm = create_bookmark(save_mock, "Test Bookmark", BookmarkType.USER, scene_id="s1")
        assert bm.id == "saved-bm-001"
        assert bm.label == "Test Bookmark"
        assert bm.bookmark_type == BookmarkType.USER
        assert bm.scene_id == "s1"

    def test_save_called_with_tags(self) -> None:
        save_mock = _make_save()
        create_bookmark(save_mock, "Test", BookmarkType.MILESTONE)
        call_kwargs = save_mock.call_args.kwargs
        assert "story" in call_kwargs["tags"]
        assert "bookmark" in call_kwargs["tags"]
        assert "milestone" in call_kwargs["tags"]


class TestListBookmarks:
    def test_lists_all(self) -> None:
        items = [
            FakeMemoryItem(
                "b1", "[Bookmark] BM1\nType: user | Chapter: None | Position: 0", ["story", "bookmark", "user"]
            ),
            FakeMemoryItem(
                "b2", "[Bookmark] BM2\nType: auto | Chapter: None | Position: 0", ["story", "bookmark", "auto"]
            ),
        ]
        bookmarks = list_bookmarks(_make_search(items))
        assert len(bookmarks) == 2

    def test_filter_by_type(self) -> None:
        items = [
            FakeMemoryItem(
                "b1", "[Bookmark] BM1\nType: user | Chapter: None | Position: 0", ["story", "bookmark", "user"]
            ),
            FakeMemoryItem(
                "b2", "[Bookmark] BM2\nType: auto | Chapter: None | Position: 0", ["story", "bookmark", "auto"]
            ),
        ]
        bookmarks = list_bookmarks(_make_search(items), BookmarkType.USER)
        assert len(bookmarks) == 1
        assert bookmarks[0].label == "BM1"

    def test_empty_result(self) -> None:
        bookmarks = list_bookmarks(_make_search([]))
        assert bookmarks == []


class TestDeleteBookmark:
    def test_delete_found(self) -> None:
        items = [
            FakeMemoryItem(
                "b1", "[Bookmark] BM1\nType: user | Chapter: None | Position: 0", ["story", "bookmark", "user"]
            ),
        ]
        update_mock = MagicMock()
        result = delete_bookmark(_make_search(items), update_mock, "b1")
        assert result is True
        update_mock.assert_called_once()

    def test_delete_not_found(self) -> None:
        update_mock = MagicMock()
        result = delete_bookmark(_make_search([]), update_mock, "nonexistent")
        assert result is False


# ===========================================================================
# Timeline Assembler Tests
# ===========================================================================


class TestAssembleTimeline:
    def test_empty_timeline(self) -> None:
        timeline = assemble_timeline(_make_search([]))
        assert timeline.entries == []
        assert timeline.chapters == {}

    def test_scenes_included(self) -> None:
        items = [
            FakeMemoryItem("s1", "[Scene] First scene\nDetails", ["story", "scene"], created_at="2026-01-01"),
            FakeMemoryItem("s2", "[Scene] Second scene\nMore", ["story", "scene"], created_at="2026-01-02"),
        ]
        timeline = assemble_timeline(_make_search(items))
        scene_entries = [e for e in timeline.entries if e.entry_type == "scene"]
        assert len(scene_entries) == 2

    def test_bookmarks_included(self) -> None:
        items = [
            FakeMemoryItem(
                "b1",
                "[Bookmark] BM1\nType: user | Chapter: Act One | Position: 1",
                ["story", "bookmark"],
                created_at="2026-01-01",
            ),
        ]
        timeline = assemble_timeline(_make_search(items))
        bm_entries = [e for e in timeline.entries if e.entry_type == "bookmark"]
        assert len(bm_entries) == 1
        assert bm_entries[0].chapter == "Act One"

    def test_sorted_by_created_at(self) -> None:
        items = [
            FakeMemoryItem("s2", "[Scene] Second\nDetails", ["story", "scene"], created_at="2026-01-02"),
            FakeMemoryItem("s1", "[Scene] First\nDetails", ["story", "scene"], created_at="2026-01-01"),
            FakeMemoryItem(
                "b1",
                "[Bookmark] Middle\nType: user | Chapter: None | Position: 0",
                ["story", "bookmark"],
                created_at="2026-01-01T12:00:00",
            ),
        ]
        timeline = assemble_timeline(_make_search(items))
        created_ats = [e.created_at for e in timeline.entries]
        assert created_ats == sorted(created_ats)

    def test_chapter_grouping(self) -> None:
        items = [
            FakeMemoryItem(
                "b1",
                "[Bookmark] BM1\nType: chapter | Chapter: Act One | Position: 0",
                ["story", "bookmark"],
                created_at="2026-01-01",
            ),
            FakeMemoryItem(
                "b2",
                "[Bookmark] BM2\nType: chapter | Chapter: Act Two | Position: 0",
                ["story", "bookmark"],
                created_at="2026-01-02",
            ),
        ]
        timeline = assemble_timeline(_make_search(items))
        assert "Act One" in timeline.chapters
        assert "Act Two" in timeline.chapters

    def test_chapter_filter(self) -> None:
        items = [
            FakeMemoryItem(
                "b1",
                "[Bookmark] BM1\nType: chapter | Chapter: Act One | Position: 0",
                ["story", "bookmark"],
                created_at="2026-01-01",
            ),
            FakeMemoryItem(
                "b2",
                "[Bookmark] BM2\nType: chapter | Chapter: Act Two | Position: 0",
                ["story", "bookmark"],
                created_at="2026-01-02",
            ),
        ]
        timeline = assemble_timeline(_make_search(items), chapter_filter="Act One")
        assert len(timeline.entries) == 1
        assert timeline.entries[0].label == "BM1"

    def test_mixed_scenes_and_bookmarks(self) -> None:
        items = [
            FakeMemoryItem("s1", "[Scene] Scene one\nText", ["story", "scene"], created_at="2026-01-01"),
            FakeMemoryItem(
                "b1",
                "[Bookmark] Midpoint\nType: milestone | Chapter: Act One | Position: 1",
                ["story", "bookmark"],
                created_at="2026-01-02",
            ),
            FakeMemoryItem("s2", "[Scene] Scene two\nText", ["story", "scene"], created_at="2026-01-03"),
        ]
        timeline = assemble_timeline(_make_search(items))
        assert len(timeline.entries) == 3
        types = [e.entry_type for e in timeline.entries]
        assert "scene" in types
        assert "bookmark" in types


class TestGetChapterList:
    def test_returns_chapters(self) -> None:
        items = [
            FakeMemoryItem(
                "b1", "[Bookmark] BM1\nType: chapter | Chapter: Act One | Position: 0", ["story", "bookmark"]
            ),
            FakeMemoryItem(
                "b2", "[Bookmark] BM2\nType: chapter | Chapter: Act Two | Position: 0", ["story", "bookmark"]
            ),
            FakeMemoryItem(
                "b3", "[Bookmark] BM3\nType: chapter | Chapter: Act One | Position: 1", ["story", "bookmark"]
            ),
        ]
        chapters = get_chapter_list(_make_search(items))
        assert chapters == ["Act One", "Act Two"]

    def test_empty(self) -> None:
        chapters = get_chapter_list(_make_search([]))
        assert chapters == []


# ===========================================================================
# Auto-Bookmark on Scene Save Tests
# ===========================================================================


class TestAutoBookmark:
    @pytest.mark.asyncio
    async def test_auto_bookmark_created_on_save(self) -> None:
        """When save_scene=True, an auto-bookmark should be created."""
        from plugins.storytelling.application.scene_handler import generate_scene

        save_mock = _make_save()

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="Scene text")

        await generate_scene(
            memory_search=_make_search(),
            memory_save=save_mock,
            llm_complete=fake_llm,
            user_prompt="Carl arrives at the lighthouse",
            save_scene=True,
        )
        # Should have been called twice: once for scene, once for auto-bookmark
        assert save_mock.call_count == 2
        # Second call should be the bookmark
        second_call = save_mock.call_args_list[1]
        assert "bookmark" in second_call.kwargs["tags"]
        assert "auto" in second_call.kwargs["tags"]

    @pytest.mark.asyncio
    async def test_no_bookmark_without_save(self) -> None:
        """No bookmark when save_scene=False."""
        from plugins.storytelling.application.scene_handler import generate_scene

        save_mock = _make_save()

        async def fake_llm(messages: Any, max_output_tokens: Any = None, temperature: Any = None) -> Any:
            return FakeLLMResponse(content="Scene text")

        await generate_scene(
            memory_search=_make_search(),
            memory_save=save_mock,
            llm_complete=fake_llm,
            user_prompt="Test",
            save_scene=False,
        )
        assert save_mock.call_count == 0


# ===========================================================================
# Handler Tests
# ===========================================================================


class TestBookmarkHandlers:
    @pytest.mark.asyncio
    async def test_bookmark_create_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_bookmark_create_handler

        task = Task(
            id="t1",
            project_id="p1",
            type="plugin.invoke",
            payload={"label": "Important moment", "bookmark_type": "user"},
        )
        ctx = {"memory_save": _make_save()}
        result = await _story_bookmark_create_handler(task, ctx)
        assert result["label"] == "Important moment"
        assert result["bookmark_type"] == "user"

    @pytest.mark.asyncio
    async def test_bookmark_create_requires_label(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_bookmark_create_handler

        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={})
        with pytest.raises(ValueError, match="label is required"):
            await _story_bookmark_create_handler(task, {"memory_save": _make_save()})

    @pytest.mark.asyncio
    async def test_bookmark_list_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_bookmark_list_handler

        items = [
            FakeMemoryItem(
                "b1", "[Bookmark] BM1\nType: user | Chapter: None | Position: 0", ["story", "bookmark", "user"]
            ),
        ]
        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={})
        result = await _story_bookmark_list_handler(task, {"memory_search": _make_search(items)})
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_timeline_handler(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_timeline_handler

        items = [
            FakeMemoryItem("s1", "[Scene] First\nText", ["story", "scene"], created_at="2026-01-01"),
        ]
        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={})
        result = await _story_timeline_handler(task, {"memory_search": _make_search(items)})
        assert result["total_entries"] == 1

    @pytest.mark.asyncio
    async def test_timeline_handler_requires_search(self) -> None:
        from openchronicle.core.domain.models.project import Task
        from plugins.storytelling.plugin import _story_timeline_handler

        task = Task(id="t1", project_id="p1", type="plugin.invoke", payload={})
        with pytest.raises(RuntimeError, match="memory_search"):
            await _story_timeline_handler(task, {})


class TestHandlerRegistration:
    def test_bookmark_timeline_handlers_registered(self) -> None:
        from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
        from plugins.storytelling.plugin import register

        handler_registry = TaskHandlerRegistry()
        plugin_registry = MagicMock()
        register(plugin_registry, handler_registry)

        for name in ("story.bookmark.create", "story.bookmark.list", "story.timeline"):
            assert handler_registry.get(name) is not None, f"Handler {name} not registered"


# ===========================================================================
# CLI Tests
# ===========================================================================


class TestTimelineCLI:
    def test_bookmark_in_dispatch(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(story_command="bookmark", bookmark_command=None)
        container = MagicMock()
        with patch("builtins.print"):
            result = run(args, container)
        assert result == 1

    def test_timeline_in_dispatch(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(
            story_command="timeline",
            project_id="test-id",
            chapter=None,
        )
        container = MagicMock()
        container.storage.search_memory.return_value = []
        with patch("builtins.print"):
            result = run(args, container)
        assert result == 0

    def test_bookmark_parser_registers(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "bookmark", "create", "Test", "--project-id", "test-id"])
        assert args.bookmark_command == "create"
        assert args.label == "Test"

    def test_bookmark_list_parser(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "bookmark", "list", "--project-id", "test-id", "--type", "user"])
        assert args.bookmark_command == "list"
        assert args.type == "user"

    def test_timeline_parser_registers(self) -> None:
        from plugins.storytelling.cli import setup_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        setup_parser(sub)
        args = parser.parse_args(["story", "timeline", "--project-id", "test-id", "--chapter", "Act One"])
        assert args.story_command == "timeline"
        assert args.chapter == "Act One"

    def test_usage_includes_bookmark_timeline(self) -> None:
        from plugins.storytelling.cli import run

        args = argparse.Namespace(story_command=None)
        container = MagicMock()
        with patch("builtins.print") as mock_print:
            run(args, container)
        printed = mock_print.call_args[0][0]
        assert "bookmark" in printed
        assert "timeline" in printed

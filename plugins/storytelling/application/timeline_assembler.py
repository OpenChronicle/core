"""Timeline assembly — builds chronological timelines from scenes and bookmarks."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from ..domain.timeline import Timeline, TimelineEntry
from .bookmark_manager import _parse_bookmark

logger = logging.getLogger(__name__)


def assemble_timeline(
    memory_search: Any,
    chapter_filter: str | None = None,
) -> Timeline:
    """Assemble a chronological timeline from scenes and bookmarks.

    1. Search scenes: tags=["story", "scene"]
    2. Search bookmarks: tags=["story", "bookmark"]
    3. Parse both into TimelineEntry
    4. Sort by created_at
    5. Group by chapter
    """
    entries: list[TimelineEntry] = []

    # 1. Scenes
    scene_items = memory_search("scene", top_k=200, tags=["story", "scene"])
    for item in scene_items:
        lines = item.content.split("\n") if item.content else []
        label = lines[0][:80] if lines else "Untitled scene"
        preview = lines[-1][:120] if len(lines) > 1 else ""
        entries.append(
            TimelineEntry(
                memory_id=item.id,
                entry_type="scene",
                label=label,
                created_at=getattr(item, "created_at", ""),
                content_preview=preview,
            )
        )

    # 2. Bookmarks
    bookmark_items = memory_search("bookmark", top_k=200, tags=["story", "bookmark"])
    for item in bookmark_items:
        bm = _parse_bookmark(item.id, item.content, item.tags, getattr(item, "created_at", ""))
        if bm is not None:
            entries.append(
                TimelineEntry(
                    memory_id=item.id,
                    entry_type="bookmark",
                    label=bm.label,
                    chapter=bm.chapter,
                    position=bm.position,
                    created_at=bm.created_at,
                )
            )

    # 3. Sort by created_at
    entries.sort(key=lambda e: e.created_at)

    # 4. Filter by chapter if requested
    if chapter_filter:
        entries = [e for e in entries if e.chapter and e.chapter.lower() == chapter_filter.lower()]

    # 5. Group by chapter
    chapters: dict[str, list[TimelineEntry]] = defaultdict(list)
    for entry in entries:
        ch = entry.chapter or "Uncategorized"
        chapters[ch].append(entry)

    return Timeline(entries=entries, chapters=dict(chapters))


def get_chapter_list(memory_search: Any) -> list[str]:
    """Get a list of unique chapter names from bookmarks."""
    bookmark_items = memory_search("bookmark", top_k=200, tags=["story", "bookmark"])
    chapters: set[str] = set()
    for item in bookmark_items:
        bm = _parse_bookmark(item.id, item.content, item.tags)
        if bm and bm.chapter:
            chapters.add(bm.chapter)
    return sorted(chapters)

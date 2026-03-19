"""Memory-backed bookmark management."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from ..domain.timeline import Bookmark, BookmarkType

logger = logging.getLogger(__name__)

BOOKMARK_TAGS = ["story", "bookmark"]


def _format_bookmark_content(
    label: str,
    bookmark_type: BookmarkType,
    scene_id: str | None = None,
    chapter: str | None = None,
    position: int = 0,
) -> str:
    """Format bookmark as memory content."""
    lines = [
        f"[Bookmark] {label}",
        f"Type: {bookmark_type.value} | Chapter: {chapter or 'None'} | Position: {position}",
    ]
    if scene_id:
        lines.append(f"Scene: {scene_id}")
    return "\n".join(lines)


def _parse_bookmark(memory_id: str, content: str, tags: list[str], created_at: str = "") -> Bookmark | None:
    """Parse a bookmark from memory content."""
    lines = content.strip().split("\n")
    if not lines or not lines[0].startswith("[Bookmark]"):
        return None

    label = lines[0].replace("[Bookmark]", "").strip()
    bookmark_type = BookmarkType.USER
    chapter = None
    position = 0
    scene_id = None

    for line in lines[1:]:
        line = line.strip()
        if line.startswith("Type:"):
            parts = line.split("|")
            for part in parts:
                part = part.strip()
                if part.startswith("Type:"):
                    type_str = part.replace("Type:", "").strip()
                    with contextlib.suppress(ValueError):
                        bookmark_type = BookmarkType(type_str)
                elif part.startswith("Chapter:"):
                    ch = part.replace("Chapter:", "").strip()
                    chapter = ch if ch != "None" else None
                elif part.startswith("Position:"):
                    with contextlib.suppress(ValueError):
                        position = int(part.replace("Position:", "").strip())
        elif line.startswith("Scene:"):
            scene_id = line.replace("Scene:", "").strip()

    return Bookmark(
        id=memory_id,
        scene_id=scene_id,
        label=label,
        bookmark_type=bookmark_type,
        chapter=chapter,
        position=position,
        created_at=created_at,
    )


def create_bookmark(
    memory_save: Any,
    label: str,
    bookmark_type: BookmarkType = BookmarkType.USER,
    scene_id: str | None = None,
    chapter: str | None = None,
    position: int = 0,
) -> Bookmark:
    """Create a bookmark and save it to memory."""
    content = _format_bookmark_content(label, bookmark_type, scene_id, chapter, position)
    tags = [*BOOKMARK_TAGS, bookmark_type.value]
    result = memory_save(content=content, tags=tags)

    logger.info("Created bookmark '%s' (type=%s, id=%s)", label, bookmark_type.value, result.id)

    return Bookmark(
        id=result.id,
        scene_id=scene_id,
        label=label,
        bookmark_type=bookmark_type,
        chapter=chapter,
        position=position,
        created_at=getattr(result, "created_at", ""),
    )


def list_bookmarks(
    memory_search: Any,
    bookmark_type: BookmarkType | None = None,
) -> list[Bookmark]:
    """List bookmarks from memory, optionally filtered by type."""
    tags = list(BOOKMARK_TAGS)
    if bookmark_type:
        tags.append(bookmark_type.value)

    items = memory_search("bookmark", top_k=200, tags=tags)
    bookmarks = []
    for item in items:
        bm = _parse_bookmark(
            item.id,
            item.content,
            item.tags,
            getattr(item, "created_at", ""),
        )
        if bm is not None:
            bookmarks.append(bm)
    return bookmarks


def delete_bookmark(
    memory_search: Any,
    memory_update: Any,
    bookmark_id: str,
) -> bool:
    """Soft-delete a bookmark by removing the 'bookmark' tag."""
    items = memory_search("bookmark", top_k=200, tags=BOOKMARK_TAGS)
    for item in items:
        if item.id == bookmark_id:
            # Remove bookmark tag to soft-delete
            new_tags = [t for t in item.tags if t != "bookmark"]
            new_tags.append("bookmark-deleted")
            memory_update(memory_id=item.id, tags=new_tags)
            logger.info("Deleted bookmark %s", bookmark_id)
            return True
    return False

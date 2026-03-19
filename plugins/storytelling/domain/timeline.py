"""Domain models for bookmarks and timeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BookmarkType(Enum):
    """Types of bookmark."""

    USER = "user"
    AUTO = "auto"
    MILESTONE = "milestone"
    CHAPTER = "chapter"


@dataclass(frozen=True)
class Bookmark:
    """A bookmark referencing a scene or moment in the story."""

    id: str
    scene_id: str | None
    label: str
    bookmark_type: BookmarkType
    chapter: str | None = None
    position: int = 0
    created_at: str = ""


@dataclass
class TimelineEntry:
    """A single entry in the story timeline."""

    memory_id: str
    entry_type: str  # "scene" or "bookmark"
    label: str
    chapter: str | None = None
    position: int = 0
    created_at: str = ""
    content_preview: str = ""


@dataclass
class Timeline:
    """Assembled story timeline."""

    entries: list[TimelineEntry] = field(default_factory=list)
    chapters: dict[str, list[TimelineEntry]] = field(default_factory=dict)

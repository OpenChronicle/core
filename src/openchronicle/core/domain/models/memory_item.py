from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class MemoryItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    pinned: bool = False
    conversation_id: str | None = None
    project_id: str | None = None
    source: str = "manual"

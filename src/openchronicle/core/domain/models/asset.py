from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Asset:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    filename: str = ""
    mime_type: str = ""
    file_path: str = ""
    size_bytes: int = 0
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class AssetLink:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str = ""
    target_type: str = ""
    target_id: str = ""
    role: str = ""
    created_at: datetime = field(default_factory=_utc_now)

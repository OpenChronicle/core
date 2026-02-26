"""Domain models for media generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MediaRequest:
    """Request to generate media from a text prompt."""

    prompt: str
    media_type: str = "image"  # "image" or "video"
    model: str | None = None
    provider: str | None = None
    width: int | None = None
    height: int | None = None
    negative_prompt: str | None = None
    seed: int | None = None
    steps: int | None = None
    # Video-specific
    duration_seconds: float | None = None
    fps: int | None = None


@dataclass
class MediaResult:
    """Result of a media generation request."""

    data: bytes
    media_type: str  # "image" or "video"
    mime_type: str
    width: int | None = None
    height: int | None = None
    model: str = ""
    provider: str = ""
    seed: int | None = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

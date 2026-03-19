"""Domain models for persona extraction.

Defines the persona profile structure. Full multimodal extraction is
deferred until core Phase 6 (multimodal conversation input via asset system).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PersonaExtractionStatus(Enum):
    """Status of a persona extraction."""

    NOT_AVAILABLE = "not_available"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class PersonaSource:
    """A source used for persona extraction."""

    source_type: str  # "text", "image", "voice", "video"
    content_ref: str  # Content or reference to content
    description: str = ""


@dataclass(frozen=True)
class ExtractedPersona:
    """An extracted character persona profile."""

    character_name: str
    physical_description: str = ""
    voice_description: str = ""
    mannerisms: str = ""
    personality_traits: str = ""
    sources: tuple[PersonaSource, ...] = ()
    confidence: float = 0.0

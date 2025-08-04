"""
Memory Management Data Models

This module contains all data structures and type definitions for the OpenChronicle
memory management system.
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional, Union
from enum import Enum


class MemoryType(Enum):
    """Types of memory components."""
    CHARACTERS = "characters"
    WORLD_STATE = "world_state"
    FLAGS = "flags"
    RECENT_EVENTS = "recent_events"
    METADATA = "metadata"


@dataclass
class MemoryFlag:
    """Represents a memory flag with associated data."""
    name: str
    created: datetime
    data: Optional[Dict[str, Any]] = None


@dataclass
class RecentEvent:
    """Represents a recent event in the story."""
    description: str
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


@dataclass
class MoodEntry:
    """Represents a character mood entry."""
    mood: str
    timestamp: datetime
    reason: Optional[str] = None
    confidence: float = 1.0


@dataclass
class VoiceProfile:
    """Represents a character's voice profile."""
    speaking_style: str = ""
    vocabulary_level: str = "moderate"
    personality_traits: List[str] = field(default_factory=list)
    speaking_patterns: List[str] = field(default_factory=list)
    emotional_tendencies: List[str] = field(default_factory=list)


@dataclass
class CharacterMemory:
    """Complete character memory state."""
    name: str
    description: str = ""
    personality: str = ""
    background: str = ""
    current_mood: str = "neutral"
    mood_history: List[MoodEntry] = field(default_factory=list)
    voice_profile: VoiceProfile = field(default_factory=VoiceProfile)
    relationships: Dict[str, str] = field(default_factory=dict)
    arc_progress: Dict[str, Any] = field(default_factory=dict)
    dialogue_history: List[str] = field(default_factory=list)


@dataclass
class MemoryMetadata:
    """Memory metadata tracking."""
    last_updated: datetime
    version: str = "1.0"
    scene_count: int = 0
    character_count: int = 0


@dataclass
class MemoryState:
    """Complete memory state structure."""
    characters: Dict[str, CharacterMemory] = field(default_factory=dict)
    world_state: Dict[str, Any] = field(default_factory=dict)
    flags: List[MemoryFlag] = field(default_factory=list)
    recent_events: List[RecentEvent] = field(default_factory=list)
    metadata: MemoryMetadata = field(default_factory=lambda: MemoryMetadata(last_updated=datetime.now(UTC)))


@dataclass
class MemorySnapshot:
    """Memory snapshot for rollback functionality."""
    story_id: str
    scene_id: str
    memory_state: MemoryState
    created_at: datetime
    snapshot_type: str = "scene"


@dataclass
class CharacterUpdates:
    """Character update specification."""
    description: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    mood: Optional[str] = None
    voice_updates: Optional[Dict[str, Any]] = None
    relationship_updates: Optional[Dict[str, str]] = None
    arc_updates: Optional[Dict[str, Any]] = None


@dataclass
class MemoryUpdateResult:
    """Result of memory update operation."""
    success: bool
    message: str
    updated_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# Configuration Constants
MAX_RECENT_EVENTS = 20
MAX_MOOD_HISTORY = 20
MAX_MEMORY_SNAPSHOTS = 50
DEFAULT_CHARACTER_TEMPLATE = {
    "name": "",
    "description": "",
    "personality": "",
    "background": "",
    "current_mood": "neutral",
    "mood_history": [],
    "voice_profile": {
        "speaking_style": "",
        "vocabulary_level": "moderate",
        "personality_traits": [],
        "speaking_patterns": [],
        "emotional_tendencies": []
    },
    "relationships": {},
    "arc_progress": {},
    "dialogue_history": []
}

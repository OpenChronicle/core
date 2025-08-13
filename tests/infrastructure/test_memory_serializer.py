import pytest
from openchronicle.infrastructure.memory.engines.persistence.memory_serializer import MemorySerializer, MemoryState, CharacterMemory, MemoryFlag, RecentEvent, MemoryMetadata, MoodEntry, VoiceProfile
from datetime import datetime, UTC

def build_sample_state():
    state = MemoryState()
    state.characters["alice"] = CharacterMemory(
        name="alice",
        description="desc",
        personality="brave",
        background="bg",
        current_mood="happy",
        mood_history=[MoodEntry(mood="happy", timestamp=datetime.now(UTC), reason=None, confidence=0.9)],
        voice_profile=VoiceProfile(
            speaking_style="casual",
            vocabulary_level="moderate",
            personality_traits=[],
            speaking_patterns=[],
            emotional_tendencies=[],
        ),
        relationships={},
        arc_progress={},
        dialogue_history=[],
    )
    state.flags.append(MemoryFlag(name="flag1", created=datetime.now(UTC), data={"k":"v"}))
    state.recent_events.append(RecentEvent(description="event", timestamp=datetime.now(UTC), data=None))
    state.metadata = MemoryMetadata(last_updated=datetime.now(UTC), version="1.0", scene_count=1, character_count=1)
    return state


def test_round_trip_serialization():
    serializer = MemorySerializer()
    original = build_sample_state()
    payload = serializer.serialize_memory(original)
    restored = serializer.deserialize_memory(payload)
    assert "alice" in restored.characters
    assert restored.metadata.scene_count == 1


def test_deserialize_with_corrupt_sections():
    serializer = MemorySerializer()
    # intentionally corrupt types
    corrupt = {
        "characters": {"bob": {"mood_history": [{"mood":"sad","timestamp":"not-a-timestamp"}]}},
        "world_state": [],  # wrong type
        "flags": [{"name":"f1","created":"not-a-timestamp"}],
        "recent_events": [{"description":"e1","timestamp":"not-a-timestamp"}],
        "metadata": {"last_updated":"not-a-timestamp"},
    }
    restored = serializer.deserialize_memory(corrupt)
    # Should still yield a MemoryState object with defaults
    assert isinstance(restored, MemoryState)
    # Invalid timestamp should fallback to default metadata timestamp
    assert isinstance(restored.metadata.last_updated, datetime)


def test_serialize_with_invalid_memory_object():
    serializer = MemorySerializer()
    class Bogus: pass
    bogus = Bogus()
    # Force attribute errors by passing wrong object type
    result = serializer.serialize_memory(bogus)  # type: ignore[arg-type]
    assert "metadata" in result
    assert result["metadata"].get("error", "").startswith("serialization_error")

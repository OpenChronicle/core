from datetime import datetime, UTC
from openchronicle.infrastructure.memory.engines.persistence.memory_repository import MemoryRepository, MemoryState


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    repo = MemoryRepository()
    story_id = "story_repo_test"

    # Build simple memory
    mem = MemoryState()
    mem.metadata.scene_count = 5
    mem.metadata.character_count = 2
    mem.metadata.last_updated = datetime.now(UTC)

    assert repo.save_memory(story_id, mem) is True
    loaded = repo.load_memory(story_id)
    assert isinstance(loaded, MemoryState)
    assert loaded.metadata.scene_count == 5


def test_load_missing_story_returns_default():
    repo = MemoryRepository()
    loaded = repo.load_memory("nonexistent_story")
    assert isinstance(loaded, MemoryState)
    # Default should have 0 scene_count
    assert loaded.metadata.scene_count == 0

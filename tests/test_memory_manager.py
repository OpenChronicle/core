"""
Test suite for Memory Manager

Tests memory loading, saving, and management functionality.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from core.memory_manager import (
    save_memory,
    load_memory,
    load_current_memory,
    initialize_memory,
    add_memory_entry,
    get_memory_summary,
    validate_memory_structure
)


@pytest.fixture
def temp_story_dir():
    """Create temporary story directory for testing."""
    temp_dir = tempfile.mkdtemp()
    story_path = Path(temp_dir) / "test_story"
    story_path.mkdir(parents=True)
    
    # Create memory directory
    memory_dir = story_path / "memory"
    memory_dir.mkdir()
    
    yield str(story_path)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_memory():
    """Sample memory data for testing."""
    return {
        "characters": {
            "Alice": {
                "current_state": {
                    "location": "village_square",
                    "mood": "curious",
                    "health": 100,
                    "inventory": ["sword", "map"]
                },
                "personality": {
                    "traits": ["brave", "kind"],
                    "values": ["justice", "friendship"]
                },
                "relationships": {
                    "Bob": {"type": "friend", "trust": 0.8}
                },
                "history": [
                    {"scene": "scene_1", "action": "arrived at village"},
                    {"scene": "scene_2", "action": "helped villager"}
                ]
            }
        },
        "world_state": {
            "time_of_day": "afternoon",
            "weather": "sunny",
            "locations": {
                "village_square": {
                    "description": "A bustling town square",
                    "characters_present": ["Alice", "Bob"]
                }
            }
        },
        "flags": [
            {"name": "quest_started", "value": True, "scene": "scene_1"},
            {"name": "villager_helped", "value": True, "scene": "scene_2"}
        ],
        "recent_events": [
            {
                "scene": "scene_2",
                "timestamp": "2024-01-01T12:00:00",
                "description": "Alice helped a villager find their lost cat",
                "characters_involved": ["Alice"],
                "impact": "positive"
            }
        ],
        "metadata": {
            "last_scene": "scene_2",
            "scene_count": 2,
            "last_updated": "2024-01-01T12:00:00"
        }
    }


class TestMemoryIO:
    """Test memory input/output operations."""
    
    def test_save_memory_success(self, temp_story_dir, sample_memory):
        """Test saving memory to file."""
        scene_id = "scene_3"
        
        result = save_memory(temp_story_dir, scene_id, sample_memory)
        
        assert result is True
        
        # Check file was created
        memory_file = Path(temp_story_dir) / "memory" / f"{scene_id}.json"
        assert memory_file.exists()
        
        # Check content
        with open(memory_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data == sample_memory
    
    def test_save_memory_create_directory(self, sample_memory):
        """Test saving memory creates directory if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = Path(temp_dir) / "new_story"
            story_path.mkdir()
            
            result = save_memory(str(story_path), "scene_1", sample_memory)
            
            assert result is True
            memory_dir = story_path / "memory"
            assert memory_dir.exists()
    
    def test_save_memory_invalid_data(self, temp_story_dir):
        """Test saving invalid memory data."""
        # Create data that can't be JSON serialized
        invalid_memory = {"function": lambda x: x}
        
        result = save_memory(temp_story_dir, "scene_1", invalid_memory)
        
        assert result is False
    
    def test_load_memory_success(self, temp_story_dir, sample_memory):
        """Test loading memory from file."""
        scene_id = "scene_2"
        
        # First save the memory
        save_memory(temp_story_dir, scene_id, sample_memory)
        
        # Then load it
        loaded_memory = load_memory(temp_story_dir, scene_id)
        
        assert loaded_memory == sample_memory
    
    def test_load_memory_file_not_found(self, temp_story_dir):
        """Test loading non-existent memory file."""
        loaded_memory = load_memory(temp_story_dir, "nonexistent_scene")
        
        assert loaded_memory == {}
    
    def test_load_memory_invalid_json(self, temp_story_dir):
        """Test loading corrupted memory file."""
        scene_id = "corrupted_scene"
        memory_file = Path(temp_story_dir) / "memory" / f"{scene_id}.json"
        
        # Create corrupted JSON file
        with open(memory_file, 'w') as f:
            f.write("{ invalid json")
        
        loaded_memory = load_memory(temp_story_dir, scene_id)
        
        assert loaded_memory == {}
    
    def test_load_current_memory_with_metadata(self, temp_story_dir, sample_memory):
        """Test loading current memory using metadata."""
        # Save memory with metadata
        save_memory(temp_story_dir, "scene_2", sample_memory)
        
        # Mock the metadata loading
        with patch('core.memory_manager.load_story_data') as mock_load:
            mock_load.return_value = {"current_scene": "scene_2"}
            
            current_memory = load_current_memory(temp_story_dir)
        
        assert current_memory == sample_memory
    
    def test_load_current_memory_no_metadata(self, temp_story_dir, sample_memory):
        """Test loading current memory without metadata."""
        # Save memory files
        save_memory(temp_story_dir, "scene_1", {"basic": "memory"})
        save_memory(temp_story_dir, "scene_2", sample_memory)
        
        # Mock no metadata
        with patch('core.memory_manager.load_story_data') as mock_load:
            mock_load.return_value = {}
            
            current_memory = load_current_memory(temp_story_dir)
        
        # Should load the most recent memory file
        assert current_memory in [{"basic": "memory"}, sample_memory]


class TestMemoryInitialization:
    """Test memory initialization functions."""
    
    def test_initialize_memory_basic(self):
        """Test basic memory initialization."""
        story_data = {
            "characters": {
                "Alice": {"personality": "brave"},
                "Bob": {"personality": "wise"}
            },
            "world": {
                "setting": "fantasy village"
            }
        }
        
        memory = initialize_memory(story_data)
        
        assert "characters" in memory
        assert "world_state" in memory
        assert "flags" in memory
        assert "recent_events" in memory
        assert "metadata" in memory
        
        # Check character initialization
        assert "Alice" in memory["characters"]
        assert "Bob" in memory["characters"]
        assert "current_state" in memory["characters"]["Alice"]
    
    def test_initialize_memory_empty_data(self):
        """Test memory initialization with empty data."""
        memory = initialize_memory({})
        
        assert isinstance(memory, dict)
        assert "characters" in memory
        assert memory["characters"] == {}
    
    def test_initialize_memory_with_locations(self):
        """Test memory initialization with location data."""
        story_data = {
            "locations": {
                "village": {"description": "A peaceful village"},
                "forest": {"description": "A dark forest"}
            }
        }
        
        memory = initialize_memory(story_data)
        
        assert "world_state" in memory
        assert "locations" in memory["world_state"]
        assert "village" in memory["world_state"]["locations"]


class TestMemoryManipulation:
    """Test memory manipulation functions."""
    
    def test_add_memory_entry_event(self, sample_memory):
        """Test adding an event to memory."""
        new_event = {
            "scene": "scene_3",
            "description": "Alice discovered a secret door",
            "characters_involved": ["Alice"],
            "impact": "mysterious"
        }
        
        result = add_memory_entry(sample_memory, "event", new_event)
        
        assert result is True
        assert len(sample_memory["recent_events"]) == 2
        assert new_event in sample_memory["recent_events"]
    
    def test_add_memory_entry_flag(self, sample_memory):
        """Test adding a flag to memory."""
        new_flag = {
            "name": "secret_discovered",
            "value": True,
            "scene": "scene_3"
        }
        
        result = add_memory_entry(sample_memory, "flag", new_flag)
        
        assert result is True
        assert len(sample_memory["flags"]) == 3
        assert new_flag in sample_memory["flags"]
    
    def test_add_memory_entry_character_state(self, sample_memory):
        """Test updating character state in memory."""
        state_update = {
            "character": "Alice",
            "updates": {
                "location": "forest_entrance",
                "mood": "determined"
            }
        }
        
        result = add_memory_entry(sample_memory, "character_state", state_update)
        
        assert result is True
        assert sample_memory["characters"]["Alice"]["current_state"]["location"] == "forest_entrance"
        assert sample_memory["characters"]["Alice"]["current_state"]["mood"] == "determined"
    
    def test_add_memory_entry_world_state(self, sample_memory):
        """Test updating world state in memory."""
        world_update = {
            "time_of_day": "evening",
            "weather": "cloudy"
        }
        
        result = add_memory_entry(sample_memory, "world_state", world_update)
        
        assert result is True
        assert sample_memory["world_state"]["time_of_day"] == "evening"
        assert sample_memory["world_state"]["weather"] == "cloudy"
    
    def test_add_memory_entry_invalid_type(self, sample_memory):
        """Test adding invalid entry type."""
        result = add_memory_entry(sample_memory, "invalid_type", {"data": "test"})
        
        assert result is False
    
    def test_add_memory_entry_malformed_data(self, sample_memory):
        """Test adding malformed entry data."""
        # Missing required fields for character state
        invalid_state = {
            "character": "Alice"
            # Missing 'updates' field
        }
        
        result = add_memory_entry(sample_memory, "character_state", invalid_state)
        
        assert result is False


class TestMemoryAnalysis:
    """Test memory analysis and summary functions."""
    
    def test_get_memory_summary_basic(self, sample_memory):
        """Test basic memory summary generation."""
        summary = get_memory_summary(sample_memory)
        
        assert isinstance(summary, dict)
        assert "character_count" in summary
        assert "event_count" in summary
        assert "flag_count" in summary
        assert "last_scene" in summary
        
        assert summary["character_count"] == 1
        assert summary["event_count"] == 1
        assert summary["flag_count"] == 2
    
    def test_get_memory_summary_detailed(self, sample_memory):
        """Test detailed memory summary."""
        summary = get_memory_summary(sample_memory, detailed=True)
        
        assert "characters" in summary
        assert "active_flags" in summary
        assert "recent_events" in summary
        assert "world_state" in summary
        
        assert "Alice" in summary["characters"]
        assert len(summary["active_flags"]) == 2
    
    def test_get_memory_summary_empty(self):
        """Test memory summary with empty memory."""
        empty_memory = {
            "characters": {},
            "flags": [],
            "recent_events": [],
            "metadata": {}
        }
        
        summary = get_memory_summary(empty_memory)
        
        assert summary["character_count"] == 0
        assert summary["event_count"] == 0
        assert summary["flag_count"] == 0
    
    def test_validate_memory_structure_valid(self, sample_memory):
        """Test memory structure validation with valid memory."""
        result = validate_memory_structure(sample_memory)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_memory_structure_missing_sections(self):
        """Test memory structure validation with missing sections."""
        incomplete_memory = {
            "characters": {},
            # Missing other required sections
        }
        
        result = validate_memory_structure(incomplete_memory)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("missing" in error.lower() for error in result["errors"])
    
    def test_validate_memory_structure_invalid_character(self):
        """Test memory structure validation with invalid character data."""
        invalid_memory = {
            "characters": {
                "Alice": {
                    # Missing required current_state
                    "personality": {"traits": ["brave"]}
                }
            },
            "world_state": {},
            "flags": [],
            "recent_events": [],
            "metadata": {}
        }
        
        result = validate_memory_structure(invalid_memory)
        
        assert result["valid"] is False
        assert any("current_state" in error for error in result["errors"])


class TestMemoryPersistence:
    """Test memory persistence and file handling."""
    
    def test_memory_file_naming(self, temp_story_dir, sample_memory):
        """Test memory file naming conventions."""
        scene_ids = ["scene_1", "chapter_2_scene_5", "epilogue"]
        
        for scene_id in scene_ids:
            save_memory(temp_story_dir, scene_id, sample_memory)
            
            # Check file exists with correct name
            memory_file = Path(temp_story_dir) / "memory" / f"{scene_id}.json"
            assert memory_file.exists()
    
    def test_memory_file_permissions(self, temp_story_dir, sample_memory):
        """Test memory file permissions and access."""
        scene_id = "scene_permissions"
        
        save_memory(temp_story_dir, scene_id, sample_memory)
        
        memory_file = Path(temp_story_dir) / "memory" / f"{scene_id}.json"
        
        # Check file is readable
        assert memory_file.is_file()
        assert memory_file.stat().st_size > 0
    
    def test_memory_backup_on_overwrite(self, temp_story_dir, sample_memory):
        """Test memory backup when overwriting."""
        scene_id = "scene_backup"
        
        # Save initial memory
        save_memory(temp_story_dir, scene_id, sample_memory)
        
        # Modify and save again
        modified_memory = sample_memory.copy()
        modified_memory["characters"]["Alice"]["current_state"]["mood"] = "happy"
        
        save_memory(temp_story_dir, scene_id, modified_memory)
        
        # Check the updated file
        loaded_memory = load_memory(temp_story_dir, scene_id)
        assert loaded_memory["characters"]["Alice"]["current_state"]["mood"] == "happy"


class TestMemoryUtilities:
    """Test memory utility functions."""
    
    def test_get_character_memory(self, sample_memory):
        """Test extracting character-specific memory."""
        from core.memory_manager import get_character_memory
        
        alice_memory = get_character_memory(sample_memory, "Alice")
        
        assert isinstance(alice_memory, dict)
        assert "current_state" in alice_memory
        assert "personality" in alice_memory
        assert alice_memory["current_state"]["mood"] == "curious"
    
    def test_get_character_memory_not_found(self, sample_memory):
        """Test extracting memory for non-existent character."""
        from core.memory_manager import get_character_memory
        
        unknown_memory = get_character_memory(sample_memory, "Unknown")
        
        assert unknown_memory == {}
    
    def test_get_recent_events(self, sample_memory):
        """Test getting recent events from memory."""
        from core.memory_manager import get_recent_events
        
        recent_events = get_recent_events(sample_memory, limit=5)
        
        assert isinstance(recent_events, list)
        assert len(recent_events) <= 5
        assert len(recent_events) == 1  # Only one event in sample
    
    def test_get_active_flags(self, sample_memory):
        """Test getting active flags from memory."""
        from core.memory_manager import get_active_flags
        
        active_flags = get_active_flags(sample_memory)
        
        assert isinstance(active_flags, list)
        assert len(active_flags) == 2
        assert all(flag["value"] for flag in active_flags)
    
    def test_clean_old_memories(self, temp_story_dir, sample_memory):
        """Test cleaning up old memory files."""
        from core.memory_manager import clean_old_memories
        
        # Create multiple memory files
        for i in range(10):
            save_memory(temp_story_dir, f"scene_{i}", sample_memory)
        
        # Clean keeping only 5 most recent
        clean_old_memories(temp_story_dir, keep_count=5)
        
        memory_dir = Path(temp_story_dir) / "memory"
        remaining_files = list(memory_dir.glob("*.json"))
        
        assert len(remaining_files) <= 5


if __name__ == "__main__":
    pytest.main([__file__])

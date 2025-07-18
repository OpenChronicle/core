"""
Test suite for Scene Logger

Tests scene logging, session tracking, and history management.
"""

import pytest
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from core.scene_logger import (
    log_scene,
    get_scene_history,
    get_recent_scenes,
    export_scene_log,
    cleanup_old_scenes,
    SceneLogger,
    SceneEntry,
    validate_scene_data
)


@pytest.fixture
def temp_story_dir():
    """Create temporary story directory for testing."""
    temp_dir = tempfile.mkdtemp()
    story_path = Path(temp_dir) / "test_story"
    story_path.mkdir(parents=True)
    
    # Create scenes directory
    scenes_dir = story_path / "scenes"
    scenes_dir.mkdir()
    
    yield str(story_path)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_scene_data():
    """Sample scene data for testing."""
    return {
        "scene_id": "scene_001",
        "timestamp": "2024-01-01T12:00:00Z",
        "user_input": "Alice explores the mysterious forest.",
        "ai_response": "Alice steps into the shadowy depths of the ancient forest. The trees seem to whisper secrets as she moves deeper into the woodland.",
        "characters_involved": ["Alice"],
        "location": "enchanted_forest",
        "mood": "mysterious",
        "session_id": "session_123",
        "metadata": {
            "word_count": 25,
            "response_time": 2.5,
            "model_used": "gpt-4",
            "temperature": 0.7
        },
        "context": {
            "previous_scene": "scene_000",
            "memory_state": "exploring",
            "active_flags": ["first_adventure"]
        }
    }


@pytest.fixture
def scene_logger(temp_story_dir):
    """Create SceneLogger instance for testing."""
    return SceneLogger(temp_story_dir)


class TestSceneEntry:
    """Test SceneEntry data class."""
    
    def test_scene_entry_creation(self, sample_scene_data):
        """Test creating SceneEntry from data."""
        entry = SceneEntry.from_dict(sample_scene_data)
        
        assert entry.scene_id == "scene_001"
        assert entry.user_input == "Alice explores the mysterious forest."
        assert "Alice" in entry.characters_involved
        assert entry.location == "enchanted_forest"
    
    def test_scene_entry_to_dict(self, sample_scene_data):
        """Test converting SceneEntry to dictionary."""
        entry = SceneEntry.from_dict(sample_scene_data)
        entry_dict = entry.to_dict()
        
        assert entry_dict["scene_id"] == sample_scene_data["scene_id"]
        assert entry_dict["user_input"] == sample_scene_data["user_input"]
        assert entry_dict["characters_involved"] == sample_scene_data["characters_involved"]
    
    def test_scene_entry_validation(self):
        """Test SceneEntry validation."""
        valid_data = {
            "scene_id": "test_scene",
            "timestamp": "2024-01-01T12:00:00Z",
            "user_input": "Test input",
            "ai_response": "Test response"
        }
        
        entry = SceneEntry.from_dict(valid_data)
        assert entry.scene_id == "test_scene"
        
        # Test with missing required field
        invalid_data = {
            "scene_id": "test_scene",
            # Missing timestamp
            "user_input": "Test input"
        }
        
        with pytest.raises(KeyError):
            SceneEntry.from_dict(invalid_data)
    
    def test_scene_entry_defaults(self):
        """Test SceneEntry default values."""
        minimal_data = {
            "scene_id": "minimal_scene",
            "timestamp": "2024-01-01T12:00:00Z",
            "user_input": "Test input",
            "ai_response": "Test response"
        }
        
        entry = SceneEntry.from_dict(minimal_data)
        
        assert entry.characters_involved == []
        assert entry.location is None
        assert entry.metadata == {}


class TestSceneLogging:
    """Test basic scene logging functionality."""
    
    def test_log_scene_success(self, temp_story_dir, sample_scene_data):
        """Test successful scene logging."""
        result = log_scene(temp_story_dir, sample_scene_data)
        
        assert result is True
        
        # Check scene file was created
        scene_file = Path(temp_story_dir) / "scenes" / "scene_001.json"
        assert scene_file.exists()
        
        # Check content
        with open(scene_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["scene_id"] == "scene_001"
        assert saved_data["user_input"] == sample_scene_data["user_input"]
    
    def test_log_scene_create_directory(self, sample_scene_data):
        """Test scene logging creates directory if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            story_path = Path(temp_dir) / "new_story"
            story_path.mkdir()
            
            result = log_scene(str(story_path), sample_scene_data)
            
            assert result is True
            scenes_dir = story_path / "scenes"
            assert scenes_dir.exists()
    
    def test_log_scene_invalid_data(self, temp_story_dir):
        """Test logging invalid scene data."""
        invalid_data = {
            "scene_id": "invalid_scene",
            # Missing required fields
        }
        
        result = log_scene(temp_story_dir, invalid_data)
        
        assert result is False
    
    def test_log_scene_duplicate_id(self, temp_story_dir, sample_scene_data):
        """Test logging scene with duplicate ID."""
        # Log scene first time
        result1 = log_scene(temp_story_dir, sample_scene_data)
        assert result1 is True
        
        # Try to log same scene ID again
        duplicate_data = sample_scene_data.copy()
        duplicate_data["user_input"] = "Different input"
        
        result2 = log_scene(temp_story_dir, duplicate_data, allow_overwrite=False)
        assert result2 is False
        
        # With overwrite enabled
        result3 = log_scene(temp_story_dir, duplicate_data, allow_overwrite=True)
        assert result3 is True
    
    def test_log_scene_with_auto_id(self, temp_story_dir):
        """Test logging scene with auto-generated ID."""
        scene_data = {
            "timestamp": "2024-01-01T12:00:00Z",
            "user_input": "Auto ID test",
            "ai_response": "Response for auto ID test"
        }
        
        result = log_scene(temp_story_dir, scene_data, auto_generate_id=True)
        
        assert result is True
        
        # Should have generated an ID
        scenes_dir = Path(temp_story_dir) / "scenes"
        scene_files = list(scenes_dir.glob("*.json"))
        assert len(scene_files) == 1


class TestSceneRetrieval:
    """Test scene retrieval and history functionality."""
    
    def test_get_scene_history(self, temp_story_dir, sample_scene_data):
        """Test getting complete scene history."""
        # Create multiple scenes
        for i in range(5):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            scene_data["user_input"] = f"User input {i}"
            log_scene(temp_story_dir, scene_data)
        
        history = get_scene_history(temp_story_dir)
        
        assert isinstance(history, list)
        assert len(history) == 5
        # Should be sorted by scene_id
        assert history[0]["scene_id"] == "scene_000"
        assert history[-1]["scene_id"] == "scene_004"
    
    def test_get_scene_history_empty(self, temp_story_dir):
        """Test getting history from empty directory."""
        history = get_scene_history(temp_story_dir)
        
        assert history == []
    
    def test_get_scene_history_with_filter(self, temp_story_dir, sample_scene_data):
        """Test getting filtered scene history."""
        # Create scenes with different characters
        characters = ["Alice", "Bob", "Charlie"]
        for i, character in enumerate(characters):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            scene_data["characters_involved"] = [character]
            log_scene(temp_story_dir, scene_data)
        
        # Filter by character
        alice_scenes = get_scene_history(temp_story_dir, character_filter="Alice")
        
        assert len(alice_scenes) == 1
        assert alice_scenes[0]["characters_involved"] == ["Alice"]
    
    def test_get_recent_scenes(self, temp_story_dir, sample_scene_data):
        """Test getting recent scenes."""
        # Create scenes with different timestamps
        base_time = datetime.fromisoformat("2024-01-01T12:00:00")
        
        for i in range(10):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            timestamp = base_time + timedelta(hours=i)
            scene_data["timestamp"] = timestamp.isoformat() + "Z"
            log_scene(temp_story_dir, scene_data)
        
        recent_scenes = get_recent_scenes(temp_story_dir, limit=3)
        
        assert len(recent_scenes) == 3
        # Should be most recent first
        assert recent_scenes[0]["scene_id"] == "scene_009"
        assert recent_scenes[-1]["scene_id"] == "scene_007"
    
    def test_get_recent_scenes_time_window(self, temp_story_dir, sample_scene_data):
        """Test getting scenes within time window."""
        base_time = datetime.fromisoformat("2024-01-01T12:00:00")
        
        # Create scenes over several days
        for i in range(5):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            timestamp = base_time + timedelta(days=i)
            scene_data["timestamp"] = timestamp.isoformat() + "Z"
            log_scene(temp_story_dir, scene_data)
        
        # Get scenes from last 2 days
        recent_time = base_time + timedelta(days=3)
        recent_scenes = get_recent_scenes(
            temp_story_dir, 
            since_time=recent_time.isoformat() + "Z"
        )
        
        assert len(recent_scenes) == 2  # scenes 3 and 4


class TestSceneLogger:
    """Test SceneLogger class functionality."""
    
    def test_scene_logger_init(self, temp_story_dir):
        """Test SceneLogger initialization."""
        logger = SceneLogger(temp_story_dir)
        
        assert logger.story_path == temp_story_dir
        assert logger.scenes_dir.exists()
    
    def test_scene_logger_log_scene(self, scene_logger, sample_scene_data):
        """Test SceneLogger log_scene method."""
        result = scene_logger.log_scene(sample_scene_data)
        
        assert result is True
        assert scene_logger.get_scene_count() == 1
    
    def test_scene_logger_get_scene(self, scene_logger, sample_scene_data):
        """Test getting specific scene."""
        scene_logger.log_scene(sample_scene_data)
        
        scene = scene_logger.get_scene("scene_001")
        
        assert scene is not None
        assert scene["scene_id"] == "scene_001"
    
    def test_scene_logger_get_scene_not_found(self, scene_logger):
        """Test getting non-existent scene."""
        scene = scene_logger.get_scene("nonexistent_scene")
        
        assert scene is None
    
    def test_scene_logger_delete_scene(self, scene_logger, sample_scene_data):
        """Test deleting a scene."""
        scene_logger.log_scene(sample_scene_data)
        assert scene_logger.get_scene_count() == 1
        
        result = scene_logger.delete_scene("scene_001")
        
        assert result is True
        assert scene_logger.get_scene_count() == 0
    
    def test_scene_logger_update_scene(self, scene_logger, sample_scene_data):
        """Test updating an existing scene."""
        scene_logger.log_scene(sample_scene_data)
        
        updated_data = sample_scene_data.copy()
        updated_data["user_input"] = "Updated user input"
        
        result = scene_logger.update_scene("scene_001", updated_data)
        
        assert result is True
        
        scene = scene_logger.get_scene("scene_001")
        assert scene["user_input"] == "Updated user input"
    
    def test_scene_logger_get_session_scenes(self, scene_logger, sample_scene_data):
        """Test getting scenes by session ID."""
        # Create scenes with different session IDs
        for i in range(3):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            scene_data["session_id"] = f"session_{i % 2}"  # Alternate sessions
            scene_logger.log_scene(scene_data)
        
        session_scenes = scene_logger.get_session_scenes("session_0")
        
        assert len(session_scenes) == 2  # scenes 0 and 2
        assert all(scene["session_id"] == "session_0" for scene in session_scenes)
    
    def test_scene_logger_get_character_scenes(self, scene_logger, sample_scene_data):
        """Test getting scenes by character involvement."""
        characters = ["Alice", "Bob", "Charlie"]
        
        for i, character in enumerate(characters):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            scene_data["characters_involved"] = [character, "Alice"]  # Alice in all
            scene_logger.log_scene(scene_data)
        
        alice_scenes = scene_logger.get_character_scenes("Alice")
        bob_scenes = scene_logger.get_character_scenes("Bob")
        
        assert len(alice_scenes) == 3  # Alice in all scenes
        assert len(bob_scenes) == 1   # Bob only in one scene


class TestSceneExport:
    """Test scene export functionality."""
    
    def test_export_scene_log_json(self, temp_story_dir, sample_scene_data):
        """Test exporting scene log as JSON."""
        # Create multiple scenes
        for i in range(3):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            log_scene(temp_story_dir, scene_data)
        
        export_file = Path(temp_story_dir) / "export.json"
        result = export_scene_log(temp_story_dir, str(export_file), format="json")
        
        assert result is True
        assert export_file.exists()
        
        # Check export content
        with open(export_file, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 3
        assert exported_data[0]["scene_id"] == "scene_000"
    
    def test_export_scene_log_txt(self, temp_story_dir, sample_scene_data):
        """Test exporting scene log as text."""
        scene_data = sample_scene_data.copy()
        log_scene(temp_story_dir, scene_data)
        
        export_file = Path(temp_story_dir) / "export.txt"
        result = export_scene_log(temp_story_dir, str(export_file), format="txt")
        
        assert result is True
        assert export_file.exists()
        
        # Check export content
        with open(export_file, 'r') as f:
            content = f.read()
        
        assert "scene_001" in content
        assert sample_scene_data["user_input"] in content
    
    def test_export_scene_log_filtered(self, temp_story_dir, sample_scene_data):
        """Test exporting filtered scene log."""
        # Create scenes with different characters
        characters = ["Alice", "Bob"]
        for i, character in enumerate(characters):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            scene_data["characters_involved"] = [character]
            log_scene(temp_story_dir, scene_data)
        
        export_file = Path(temp_story_dir) / "alice_export.json"
        result = export_scene_log(
            temp_story_dir, 
            str(export_file), 
            format="json",
            character_filter="Alice"
        )
        
        assert result is True
        
        with open(export_file, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 1
        assert exported_data[0]["characters_involved"] == ["Alice"]


class TestSceneCleanup:
    """Test scene cleanup functionality."""
    
    def test_cleanup_old_scenes_by_count(self, temp_story_dir, sample_scene_data):
        """Test cleaning up old scenes by count."""
        # Create many scenes
        for i in range(10):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            log_scene(temp_story_dir, scene_data)
        
        # Keep only 5 most recent
        result = cleanup_old_scenes(temp_story_dir, keep_count=5)
        
        assert result is True
        
        remaining_scenes = get_scene_history(temp_story_dir)
        assert len(remaining_scenes) == 5
        # Should keep most recent
        assert remaining_scenes[-1]["scene_id"] == "scene_009"
    
    def test_cleanup_old_scenes_by_age(self, temp_story_dir, sample_scene_data):
        """Test cleaning up old scenes by age."""
        base_time = datetime.fromisoformat("2024-01-01T12:00:00")
        
        # Create scenes with different ages
        for i in range(5):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            timestamp = base_time + timedelta(days=i)
            scene_data["timestamp"] = timestamp.isoformat() + "Z"
            log_scene(temp_story_dir, scene_data)
        
        # Clean up scenes older than 2 days
        cutoff_time = base_time + timedelta(days=2)
        result = cleanup_old_scenes(
            temp_story_dir, 
            older_than=cutoff_time.isoformat() + "Z"
        )
        
        assert result is True
        
        remaining_scenes = get_scene_history(temp_story_dir)
        # Should keep scenes 2, 3, 4 (newer than cutoff)
        assert len(remaining_scenes) == 3
    
    def test_cleanup_old_scenes_with_backup(self, temp_story_dir, sample_scene_data):
        """Test cleaning up scenes with backup creation."""
        # Create scenes
        for i in range(5):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            log_scene(temp_story_dir, scene_data)
        
        result = cleanup_old_scenes(temp_story_dir, keep_count=2, create_backup=True)
        
        assert result is True
        
        # Check backup was created
        backup_dir = Path(temp_story_dir) / "_backups"
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob("scenes_backup_*.json"))
        assert len(backup_files) > 0


class TestSceneValidation:
    """Test scene data validation."""
    
    def test_validate_scene_data_valid(self, sample_scene_data):
        """Test validation with valid scene data."""
        result = validate_scene_data(sample_scene_data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_scene_data_missing_required(self):
        """Test validation with missing required fields."""
        invalid_data = {
            "scene_id": "test_scene",
            # Missing timestamp, user_input, ai_response
        }
        
        result = validate_scene_data(invalid_data)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_validate_scene_data_invalid_timestamp(self):
        """Test validation with invalid timestamp."""
        invalid_data = {
            "scene_id": "test_scene",
            "timestamp": "not a valid timestamp",
            "user_input": "Test input",
            "ai_response": "Test response"
        }
        
        result = validate_scene_data(invalid_data)
        
        assert result["valid"] is False
        assert any("timestamp" in error.lower() for error in result["errors"])
    
    def test_validate_scene_data_warnings(self):
        """Test validation generates warnings for missing optional fields."""
        minimal_data = {
            "scene_id": "test_scene",
            "timestamp": "2024-01-01T12:00:00Z",
            "user_input": "Test input",
            "ai_response": "Test response"
            # Missing optional fields like characters_involved, location
        }
        
        result = validate_scene_data(minimal_data)
        
        assert result["valid"] is True
        assert len(result["warnings"]) > 0


class TestSceneAnalytics:
    """Test scene analytics functionality."""
    
    def test_scene_analytics_basic_stats(self, scene_logger, sample_scene_data):
        """Test basic scene analytics."""
        # Create scenes with different metadata
        for i in range(5):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            scene_data["metadata"]["word_count"] = 20 + i * 5
            scene_data["metadata"]["response_time"] = 1.0 + i * 0.5
            scene_logger.log_scene(scene_data)
        
        stats = scene_logger.get_analytics()
        
        assert isinstance(stats, dict)
        assert "total_scenes" in stats
        assert "average_word_count" in stats
        assert "average_response_time" in stats
        assert stats["total_scenes"] == 5
    
    def test_scene_analytics_character_involvement(self, scene_logger, sample_scene_data):
        """Test character involvement analytics."""
        characters = ["Alice", "Bob", "Charlie"]
        
        # Create scenes with varying character involvement
        for i in range(6):
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            # Alice in all, Bob in half, Charlie in one
            if i < 6:
                scene_data["characters_involved"] = ["Alice"]
            if i < 3:
                scene_data["characters_involved"].append("Bob")
            if i == 0:
                scene_data["characters_involved"].append("Charlie")
            scene_logger.log_scene(scene_data)
        
        stats = scene_logger.get_analytics()
        
        assert "character_involvement" in stats
        assert stats["character_involvement"]["Alice"] == 6
        assert stats["character_involvement"]["Bob"] == 3
        assert stats["character_involvement"]["Charlie"] == 1
    
    def test_scene_analytics_temporal_patterns(self, scene_logger, sample_scene_data):
        """Test temporal pattern analytics."""
        base_time = datetime.fromisoformat("2024-01-01T08:00:00")
        
        # Create scenes at different times of day
        for i in range(24):  # One scene per hour
            scene_data = sample_scene_data.copy()
            scene_data["scene_id"] = f"scene_{i:03d}"
            timestamp = base_time + timedelta(hours=i)
            scene_data["timestamp"] = timestamp.isoformat() + "Z"
            scene_logger.log_scene(scene_data)
        
        stats = scene_logger.get_analytics()
        
        assert "temporal_patterns" in stats
        assert "scenes_by_hour" in stats["temporal_patterns"]


if __name__ == "__main__":
    pytest.main([__file__])

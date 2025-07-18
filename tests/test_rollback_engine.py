"""
Test suite for Rollback Engine

Tests story rollback, state restoration, and version management functionality.
"""

import pytest
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from core.rollback_engine import (
    RollbackEngine,
    RollbackPoint,
    create_rollback_point,
    restore_to_point,
    list_rollback_points,
    cleanup_old_rollbacks,
    validate_rollback_data
)


@pytest.fixture
def temp_story_dir():
    """Create temporary story directory for testing."""
    temp_dir = tempfile.mkdtemp()
    story_path = Path(temp_dir) / "test_story"
    story_path.mkdir(parents=True)
    
    # Create rollback directory
    rollback_dir = story_path / "rollbacks"
    rollback_dir.mkdir()
    
    yield str(story_path)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_story_state():
    """Sample story state for rollback testing."""
    return {
        "scene_id": "scene_005",
        "memory": {
            "characters": {
                "Alice": {
                    "current_state": {
                        "location": "enchanted_forest",
                        "mood": "curious",
                        "health": 85,
                        "inventory": ["sword", "map", "potion"]
                    }
                }
            },
            "world_state": {
                "time_of_day": "afternoon",
                "weather": "partly_cloudy"
            },
            "flags": [
                {"name": "quest_started", "value": True},
                {"name": "met_wizard", "value": True}
            ]
        },
        "scene_history": [
            {"scene_id": "scene_001", "summary": "Adventure begins"},
            {"scene_id": "scene_002", "summary": "Meet companion"},
            {"scene_id": "scene_003", "summary": "Enter forest"},
            {"scene_id": "scene_004", "summary": "Discover ruins"},
            {"scene_id": "scene_005", "summary": "Current scene"}
        ],
        "metadata": {
            "session_id": "session_123",
            "last_updated": "2024-01-01T14:00:00Z",
            "word_count": 1250
        }
    }


@pytest.fixture
def rollback_engine(temp_story_dir):
    """Create RollbackEngine instance for testing."""
    return RollbackEngine(temp_story_dir)


class TestRollbackPoint:
    """Test RollbackPoint data structure."""
    
    def test_rollback_point_creation(self, sample_story_state):
        """Test creating RollbackPoint from state data."""
        point_id = "rollback_001"
        description = "Before entering dangerous area"
        
        rollback_point = RollbackPoint.create(
            point_id=point_id,
            description=description,
            story_state=sample_story_state
        )
        
        assert rollback_point.point_id == point_id
        assert rollback_point.description == description
        assert rollback_point.story_state == sample_story_state
        assert rollback_point.timestamp is not None
    
    def test_rollback_point_to_dict(self, sample_story_state):
        """Test converting RollbackPoint to dictionary."""
        rollback_point = RollbackPoint.create(
            point_id="test_point",
            description="Test rollback point",
            story_state=sample_story_state
        )
        
        point_dict = rollback_point.to_dict()
        
        assert point_dict["point_id"] == "test_point"
        assert point_dict["description"] == "Test rollback point"
        assert point_dict["story_state"] == sample_story_state
        assert "timestamp" in point_dict
    
    def test_rollback_point_from_dict(self, sample_story_state):
        """Test creating RollbackPoint from dictionary."""
        point_data = {
            "point_id": "dict_point",
            "description": "Point from dict",
            "story_state": sample_story_state,
            "timestamp": "2024-01-01T12:00:00Z",
            "metadata": {"auto_created": False}
        }
        
        rollback_point = RollbackPoint.from_dict(point_data)
        
        assert rollback_point.point_id == "dict_point"
        assert rollback_point.description == "Point from dict"
        assert rollback_point.metadata["auto_created"] is False
    
    def test_rollback_point_validation(self):
        """Test RollbackPoint validation."""
        valid_data = {
            "point_id": "valid_point",
            "description": "Valid rollback point",
            "story_state": {"scene_id": "test_scene"},
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        point = RollbackPoint.from_dict(valid_data)
        assert point.point_id == "valid_point"
        
        # Test with missing required field
        invalid_data = {
            "point_id": "invalid_point",
            # Missing story_state
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        with pytest.raises(KeyError):
            RollbackPoint.from_dict(invalid_data)


class TestRollbackEngine:
    """Test RollbackEngine functionality."""
    
    def test_rollback_engine_init(self, temp_story_dir):
        """Test RollbackEngine initialization."""
        engine = RollbackEngine(temp_story_dir)
        
        assert engine.story_path == temp_story_dir
        assert engine.rollback_dir.exists()
        assert hasattr(engine, 'max_rollback_points')
    
    def test_create_rollback_point(self, rollback_engine, sample_story_state):
        """Test creating a rollback point."""
        point_id = "manual_save_001"
        description = "Before boss battle"
        
        result = rollback_engine.create_point(
            point_id=point_id,
            description=description,
            story_state=sample_story_state
        )
        
        assert result is True
        
        # Verify point was saved
        point_file = rollback_engine.rollback_dir / f"{point_id}.json"
        assert point_file.exists()
        
        # Verify content
        with open(point_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["point_id"] == point_id
        assert saved_data["description"] == description
    
    def test_create_auto_rollback_point(self, rollback_engine, sample_story_state):
        """Test creating automatic rollback point."""
        result = rollback_engine.create_auto_point(story_state=sample_story_state)
        
        assert result is not None  # Should return point_id
        
        # Verify auto point was created
        rollback_files = list(rollback_engine.rollback_dir.glob("auto_*.json"))
        assert len(rollback_files) >= 1
    
    def test_list_rollback_points(self, rollback_engine, sample_story_state):
        """Test listing available rollback points."""
        # Create multiple rollback points
        points = [
            ("point_001", "First save"),
            ("point_002", "Second save"),
            ("point_003", "Third save")
        ]
        
        for point_id, description in points:
            rollback_engine.create_point(point_id, description, sample_story_state)
        
        available_points = rollback_engine.list_points()
        
        assert len(available_points) == 3
        assert all(point["point_id"] in ["point_001", "point_002", "point_003"] for point in available_points)
    
    def test_get_rollback_point(self, rollback_engine, sample_story_state):
        """Test getting specific rollback point."""
        point_id = "specific_point"
        rollback_engine.create_point(point_id, "Specific test point", sample_story_state)
        
        rollback_point = rollback_engine.get_point(point_id)
        
        assert rollback_point is not None
        assert rollback_point.point_id == point_id
        assert rollback_point.description == "Specific test point"
    
    def test_get_rollback_point_not_found(self, rollback_engine):
        """Test getting non-existent rollback point."""
        rollback_point = rollback_engine.get_point("nonexistent_point")
        
        assert rollback_point is None
    
    def test_delete_rollback_point(self, rollback_engine, sample_story_state):
        """Test deleting a rollback point."""
        point_id = "delete_test_point"
        rollback_engine.create_point(point_id, "Point to delete", sample_story_state)
        
        # Verify point exists
        assert rollback_engine.get_point(point_id) is not None
        
        # Delete point
        result = rollback_engine.delete_point(point_id)
        
        assert result is True
        assert rollback_engine.get_point(point_id) is None
    
    def test_restore_to_point(self, rollback_engine, sample_story_state):
        """Test restoring to a rollback point."""
        point_id = "restore_test_point"
        rollback_engine.create_point(point_id, "Point for restoration", sample_story_state)
        
        # Mock the story state restoration
        with patch.object(rollback_engine, '_restore_story_state') as mock_restore:
            mock_restore.return_value = True
            
            result = rollback_engine.restore_to_point(point_id)
        
        assert result is True
        mock_restore.assert_called_once()
    
    def test_restore_to_nonexistent_point(self, rollback_engine):
        """Test restoring to non-existent rollback point."""
        result = rollback_engine.restore_to_point("nonexistent_point")
        
        assert result is False
    
    def test_cleanup_old_rollbacks(self, rollback_engine, sample_story_state):
        """Test cleaning up old rollback points."""
        # Create multiple rollback points
        base_time = datetime.fromisoformat("2024-01-01T12:00:00")
        
        for i in range(10):
            point_id = f"cleanup_point_{i:03d}"
            rollback_engine.create_point(point_id, f"Point {i}", sample_story_state)
            
            # Modify timestamp to simulate different creation times
            point_file = rollback_engine.rollback_dir / f"{point_id}.json"
            with open(point_file, 'r') as f:
                point_data = json.load(f)
            
            # Make older points
            timestamp = base_time + timedelta(hours=i)
            point_data["timestamp"] = timestamp.isoformat() + "Z"
            
            with open(point_file, 'w') as f:
                json.dump(point_data, f)
        
        # Keep only 5 most recent
        cleaned_count = rollback_engine.cleanup_old_points(keep_count=5)
        
        assert cleaned_count == 5
        remaining_points = rollback_engine.list_points()
        assert len(remaining_points) == 5
    
    def test_get_rollback_history(self, rollback_engine, sample_story_state):
        """Test getting rollback history."""
        # Create points with different states
        for i in range(3):
            state = sample_story_state.copy()
            state["scene_id"] = f"scene_{i:03d}"
            rollback_engine.create_point(f"history_point_{i}", f"Point {i}", state)
        
        history = rollback_engine.get_rollback_history()
        
        assert isinstance(history, list)
        assert len(history) == 3
        # Should be sorted by timestamp (most recent first)
        assert all("point_id" in point for point in history)


class TestRollbackFunctions:
    """Test standalone rollback functions."""
    
    def test_create_rollback_point_function(self, temp_story_dir, sample_story_state):
        """Test standalone create_rollback_point function."""
        point_id = "function_test_point"
        description = "Test rollback point"
        
        result = create_rollback_point(
            temp_story_dir,
            point_id,
            description,
            sample_story_state
        )
        
        assert result is True
        
        # Verify point was created
        point_file = Path(temp_story_dir) / "rollbacks" / f"{point_id}.json"
        assert point_file.exists()
    
    def test_restore_to_point_function(self, temp_story_dir, sample_story_state):
        """Test standalone restore_to_point function."""
        point_id = "restore_function_test"
        
        # Create rollback point first
        create_rollback_point(temp_story_dir, point_id, "Test restore", sample_story_state)
        
        # Mock the actual restoration
        with patch('core.rollback_engine.restore_story_state') as mock_restore:
            mock_restore.return_value = True
            
            result = restore_to_point(temp_story_dir, point_id)
        
        assert result is True
    
    def test_list_rollback_points_function(self, temp_story_dir, sample_story_state):
        """Test standalone list_rollback_points function."""
        # Create multiple points
        for i in range(3):
            create_rollback_point(
                temp_story_dir,
                f"list_test_point_{i}",
                f"Test point {i}",
                sample_story_state
            )
        
        points = list_rollback_points(temp_story_dir)
        
        assert len(points) == 3
        assert all("point_id" in point for point in points)
    
    def test_cleanup_old_rollbacks_function(self, temp_story_dir, sample_story_state):
        """Test standalone cleanup_old_rollbacks function."""
        # Create multiple points
        for i in range(8):
            create_rollback_point(
                temp_story_dir,
                f"cleanup_function_test_{i}",
                f"Cleanup test {i}",
                sample_story_state
            )
        
        # Keep only 3 most recent
        cleaned_count = cleanup_old_rollbacks(temp_story_dir, keep_count=3)
        
        assert cleaned_count == 5  # 8 - 3 = 5 cleaned
        
        remaining_points = list_rollback_points(temp_story_dir)
        assert len(remaining_points) == 3
    
    def test_validate_rollback_data_valid(self, sample_story_state):
        """Test rollback data validation with valid data."""
        rollback_data = {
            "point_id": "test_point",
            "description": "Test validation",
            "story_state": sample_story_state,
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        result = validate_rollback_data(rollback_data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_rollback_data_invalid(self):
        """Test rollback data validation with invalid data."""
        invalid_data = {
            "point_id": "test_point",
            # Missing required fields
        }
        
        result = validate_rollback_data(invalid_data)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestRollbackStrategies:
    """Test different rollback strategies."""
    
    def test_smart_rollback_strategy(self, rollback_engine, sample_story_state):
        """Test smart rollback point creation strategy."""
        # Configure smart strategy
        rollback_engine.set_strategy("smart", {
            "scene_threshold": 3,
            "time_threshold": 300,  # 5 minutes
            "major_events": ["combat", "discovery", "character_death"]
        })
        
        # Simulate conditions that should trigger auto-rollback
        state_with_combat = sample_story_state.copy()
        state_with_combat["metadata"]["event_type"] = "combat"
        
        auto_point_id = rollback_engine.check_auto_rollback(state_with_combat)
        
        assert auto_point_id is not None
    
    def test_conservative_rollback_strategy(self, rollback_engine, sample_story_state):
        """Test conservative rollback strategy."""
        rollback_engine.set_strategy("conservative", {
            "scene_threshold": 1,  # Create point every scene
            "always_create": True
        })
        
        auto_point_id = rollback_engine.check_auto_rollback(sample_story_state)
        
        assert auto_point_id is not None
    
    def test_minimal_rollback_strategy(self, rollback_engine, sample_story_state):
        """Test minimal rollback strategy."""
        rollback_engine.set_strategy("minimal", {
            "scene_threshold": 10,  # Very high threshold
            "major_events_only": True
        })
        
        # Normal scene shouldn't trigger auto-rollback
        auto_point_id = rollback_engine.check_auto_rollback(sample_story_state)
        
        assert auto_point_id is None


class TestRollbackAnalytics:
    """Test rollback analytics and reporting."""
    
    def test_rollback_usage_statistics(self, rollback_engine, sample_story_state):
        """Test rollback usage statistics."""
        # Create and use rollback points
        for i in range(5):
            point_id = f"stats_point_{i}"
            rollback_engine.create_point(point_id, f"Stats point {i}", sample_story_state)
            
            if i % 2 == 0:  # Restore some points
                with patch.object(rollback_engine, '_restore_story_state') as mock_restore:
                    mock_restore.return_value = True
                    rollback_engine.restore_to_point(point_id)
        
        stats = rollback_engine.get_usage_statistics()
        
        assert isinstance(stats, dict)
        assert "total_points_created" in stats
        assert "total_restorations" in stats
        assert "most_used_point" in stats
    
    def test_rollback_impact_analysis(self, rollback_engine, sample_story_state):
        """Test analyzing impact of rollbacks on story."""
        # Create points representing story branches
        original_state = sample_story_state.copy()
        rollback_engine.create_point("branch_point", "Story branch", original_state)
        
        # Simulate different story paths
        alternate_state = sample_story_state.copy()
        alternate_state["scene_id"] = "alternate_scene"
        alternate_state["memory"]["flags"].append({"name": "alternate_path", "value": True})
        
        impact_analysis = rollback_engine.analyze_story_impact("branch_point", alternate_state)
        
        assert isinstance(impact_analysis, dict)
        assert "changes_detected" in impact_analysis
        assert "impact_score" in impact_analysis
    
    def test_rollback_patterns_analysis(self, rollback_engine, sample_story_state):
        """Test analyzing rollback usage patterns."""
        # Create pattern of rollbacks
        base_time = datetime.fromisoformat("2024-01-01T12:00:00")
        
        for i in range(10):
            state = sample_story_state.copy()
            state["scene_id"] = f"pattern_scene_{i}"
            
            point_id = f"pattern_point_{i}"
            rollback_engine.create_point(point_id, f"Pattern point {i}", state)
            
            # Simulate restoration pattern
            if i > 0 and i % 3 == 0:  # Restore every 3rd point
                with patch.object(rollback_engine, '_restore_story_state') as mock_restore:
                    mock_restore.return_value = True
                    rollback_engine.restore_to_point(f"pattern_point_{i-1}")
        
        patterns = rollback_engine.analyze_usage_patterns()
        
        assert isinstance(patterns, dict)
        assert "restoration_frequency" in patterns
        assert "average_rollback_distance" in patterns


class TestRollbackIntegration:
    """Test rollback integration with other systems."""
    
    def test_rollback_with_memory_system(self, rollback_engine, sample_story_state):
        """Test rollback integration with memory system."""
        point_id = "memory_integration_test"
        rollback_engine.create_point(point_id, "Memory test", sample_story_state)
        
        # Mock memory system integration
        with patch('core.rollback_engine.save_memory') as mock_save_memory, \
             patch('core.rollback_engine.load_memory') as mock_load_memory:
            
            mock_load_memory.return_value = sample_story_state["memory"]
            
            result = rollback_engine.restore_to_point(point_id)
        
        assert result is True
        mock_save_memory.assert_called()
    
    def test_rollback_with_scene_logger(self, rollback_engine, sample_story_state):
        """Test rollback integration with scene logging."""
        point_id = "scene_integration_test"
        rollback_engine.create_point(point_id, "Scene test", sample_story_state)
        
        # Mock scene logger integration
        with patch('core.rollback_engine.truncate_scene_history') as mock_truncate:
            result = rollback_engine.restore_to_point(point_id)
        
        assert result is True
        mock_truncate.assert_called()
    
    def test_rollback_with_timeline_builder(self, rollback_engine, sample_story_state):
        """Test rollback integration with timeline system."""
        point_id = "timeline_integration_test"
        rollback_engine.create_point(point_id, "Timeline test", sample_story_state)
        
        # Mock timeline integration
        with patch('core.rollback_engine.rebuild_timeline') as mock_rebuild:
            result = rollback_engine.restore_to_point(point_id)
        
        assert result is True
        mock_rebuild.assert_called()


class TestErrorHandling:
    """Test error handling in rollback operations."""
    
    def test_corrupted_rollback_file(self, rollback_engine):
        """Test handling corrupted rollback files."""
        # Create corrupted rollback file
        corrupted_file = rollback_engine.rollback_dir / "corrupted_point.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json content")
        
        # Should handle gracefully
        rollback_point = rollback_engine.get_point("corrupted_point")
        assert rollback_point is None
    
    def test_insufficient_disk_space(self, rollback_engine, sample_story_state):
        """Test handling insufficient disk space."""
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            result = rollback_engine.create_point("space_test", "Test", sample_story_state)
        
        assert result is False
    
    def test_permission_denied_rollback(self, rollback_engine, sample_story_state):
        """Test handling permission denied errors."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = rollback_engine.create_point("permission_test", "Test", sample_story_state)
        
        assert result is False
    
    def test_rollback_state_corruption_detection(self, rollback_engine):
        """Test detecting corrupted story state during rollback."""
        # Create rollback point with corrupted state
        corrupted_state = {
            "scene_id": None,  # Invalid scene_id
            "memory": "not_a_dict",  # Invalid memory structure
        }
        
        validation_result = validate_rollback_data({
            "point_id": "corrupted_test",
            "description": "Corrupted state test",
            "story_state": corrupted_state,
            "timestamp": "2024-01-01T12:00:00Z"
        })
        
        assert validation_result["valid"] is False
        assert len(validation_result["errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])

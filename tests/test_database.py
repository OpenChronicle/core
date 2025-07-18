"""
Test suite for Database

Tests database operations, story data management, and persistence.
"""

import pytest
import tempfile
import shutil
import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from core.database import (
    get_story_data,
    save_story_data,
    load_story_data,
    create_story_backup,
    restore_story_backup,
    validate_story_data,
    get_story_list,
    delete_story,
    DatabaseManager
)


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    storage_path = Path(temp_dir) / "storage"
    storage_path.mkdir(parents=True)
    
    yield str(storage_path)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_story_data():
    """Sample story data for testing."""
    return {
        "id": "test_story",
        "meta": {
            "title": "Test Adventure",
            "description": "A test story for database operations",
            "author": "Test Author",
            "version": "1.0",
            "created": "2024-01-01T00:00:00Z",
            "modified": "2024-01-01T12:00:00Z"
        },
        "characters": {
            "Alice": {
                "name": "Alice",
                "personality": "brave and curious",
                "stats": {"strength": 8, "intelligence": 9, "charisma": 7}
            },
            "Bob": {
                "name": "Bob", 
                "personality": "wise and patient",
                "stats": {"strength": 6, "intelligence": 10, "charisma": 8}
            }
        },
        "world": {
            "setting": "fantasy medieval",
            "locations": {
                "village": {"name": "Peaceful Village", "description": "A quiet farming village"},
                "forest": {"name": "Dark Forest", "description": "A mysterious woodland"}
            }
        },
        "config": {
            "max_scenes": 100,
            "auto_save": True,
            "difficulty": "normal"
        }
    }


@pytest.fixture
def db_manager(temp_storage_dir):
    """Create DatabaseManager instance for testing."""
    return DatabaseManager(str(temp_storage_dir))


class TestStoryDataOperations:
    """Test basic story data operations."""
    
    def test_save_story_data_success(self, temp_storage_dir, sample_story_data):
        """Test saving story data to file."""
        story_id = "test_story"
        
        result = save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        assert result is True
        
        # Check file was created
        story_file = Path(temp_storage_dir) / story_id / "story_data.json"
        assert story_file.exists()
        
        # Check content
        with open(story_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data == sample_story_data
    
    def test_save_story_data_create_directory(self, sample_story_data):
        """Test saving story data creates directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "new_storage"
            story_id = "new_story"
            
            result = save_story_data(str(storage_path), story_id, sample_story_data)
            
            assert result is True
            assert (storage_path / story_id).exists()
            assert (storage_path / story_id / "story_data.json").exists()
    
    def test_save_story_data_invalid_data(self, temp_storage_dir):
        """Test saving invalid story data."""
        # Create data that can't be JSON serialized
        invalid_data = {"function": lambda x: x}
        
        result = save_story_data(temp_storage_dir, "test_story", invalid_data)
        
        assert result is False
    
    def test_load_story_data_success(self, temp_storage_dir, sample_story_data):
        """Test loading story data from file."""
        story_id = "test_story"
        
        # First save the data
        save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        # Then load it
        loaded_data = load_story_data(temp_storage_dir, story_id)
        
        assert loaded_data == sample_story_data
    
    def test_load_story_data_not_found(self, temp_storage_dir):
        """Test loading non-existent story data."""
        loaded_data = load_story_data(temp_storage_dir, "nonexistent_story")
        
        assert loaded_data == {}
    
    def test_load_story_data_corrupted_file(self, temp_storage_dir):
        """Test loading corrupted story data file."""
        story_id = "corrupted_story"
        story_dir = Path(temp_storage_dir) / story_id
        story_dir.mkdir(parents=True)
        
        # Create corrupted JSON file
        story_file = story_dir / "story_data.json"
        with open(story_file, 'w') as f:
            f.write("{ invalid json content")
        
        loaded_data = load_story_data(temp_storage_dir, story_id)
        
        assert loaded_data == {}
    
    def test_get_story_data_wrapper(self, temp_storage_dir, sample_story_data):
        """Test get_story_data wrapper function."""
        story_id = "test_story"
        save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        with patch('core.database.DEFAULT_STORAGE_PATH', temp_storage_dir):
            story_data = get_story_data(story_id)
        
        assert story_data == sample_story_data


class TestStoryValidation:
    """Test story data validation."""
    
    def test_validate_story_data_valid(self, sample_story_data):
        """Test validation with valid story data."""
        result = validate_story_data(sample_story_data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_story_data_missing_required(self):
        """Test validation with missing required fields."""
        invalid_data = {
            "id": "test_story",
            # Missing meta section
            "characters": {}
        }
        
        result = validate_story_data(invalid_data)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("meta" in error.lower() for error in result["errors"])
    
    def test_validate_story_data_invalid_structure(self):
        """Test validation with invalid data structure."""
        invalid_data = {
            "id": "test_story",
            "meta": "should be object not string",
            "characters": {}
        }
        
        result = validate_story_data(invalid_data)
        
        assert result["valid"] is False
        assert any("meta" in error.lower() for error in result["errors"])
    
    def test_validate_story_data_empty(self):
        """Test validation with empty data."""
        result = validate_story_data({})
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestStoryManagement:
    """Test story management operations."""
    
    def test_get_story_list(self, temp_storage_dir, sample_story_data):
        """Test getting list of available stories."""
        # Create multiple stories
        stories = ["story1", "story2", "story3"]
        for story_id in stories:
            story_data = sample_story_data.copy()
            story_data["id"] = story_id
            save_story_data(temp_storage_dir, story_id, story_data)
        
        story_list = get_story_list(temp_storage_dir)
        
        assert isinstance(story_list, list)
        assert len(story_list) == 3
        assert all(story in stories for story in story_list)
    
    def test_get_story_list_empty_directory(self, temp_storage_dir):
        """Test getting story list from empty directory."""
        story_list = get_story_list(temp_storage_dir)
        
        assert story_list == []
    
    def test_get_story_list_with_metadata(self, temp_storage_dir, sample_story_data):
        """Test getting story list with metadata."""
        story_id = "detailed_story"
        save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        story_list = get_story_list(temp_storage_dir, include_metadata=True)
        
        assert isinstance(story_list, list)
        assert len(story_list) == 1
        assert isinstance(story_list[0], dict)
        assert "id" in story_list[0]
        assert "meta" in story_list[0]
    
    def test_delete_story_success(self, temp_storage_dir, sample_story_data):
        """Test deleting a story."""
        story_id = "story_to_delete"
        save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        # Verify story exists
        assert (Path(temp_storage_dir) / story_id).exists()
        
        result = delete_story(temp_storage_dir, story_id)
        
        assert result is True
        assert not (Path(temp_storage_dir) / story_id).exists()
    
    def test_delete_story_not_found(self, temp_storage_dir):
        """Test deleting non-existent story."""
        result = delete_story(temp_storage_dir, "nonexistent_story")
        
        assert result is False
    
    def test_delete_story_with_backup(self, temp_storage_dir, sample_story_data):
        """Test deleting story with backup creation."""
        story_id = "story_with_backup"
        save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        result = delete_story(temp_storage_dir, story_id, create_backup=True)
        
        assert result is True
        # Check backup was created
        backup_dir = Path(temp_storage_dir) / "_backups"
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob(f"{story_id}_*.zip"))
        assert len(backup_files) > 0


class TestBackupOperations:
    """Test backup and restore operations."""
    
    def test_create_story_backup(self, temp_storage_dir, sample_story_data):
        """Test creating story backup."""
        story_id = "backup_test_story"
        save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        backup_path = create_story_backup(temp_storage_dir, story_id)
        
        assert backup_path is not None
        assert Path(backup_path).exists()
        assert backup_path.endswith('.zip')
        assert story_id in backup_path
    
    def test_create_story_backup_not_found(self, temp_storage_dir):
        """Test creating backup for non-existent story."""
        backup_path = create_story_backup(temp_storage_dir, "nonexistent_story")
        
        assert backup_path is None
    
    def test_restore_story_backup(self, temp_storage_dir, sample_story_data):
        """Test restoring story from backup."""
        story_id = "restore_test_story"
        save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        # Create backup
        backup_path = create_story_backup(temp_storage_dir, story_id)
        
        # Delete original
        delete_story(temp_storage_dir, story_id)
        assert not (Path(temp_storage_dir) / story_id).exists()
        
        # Restore from backup
        result = restore_story_backup(temp_storage_dir, backup_path)
        
        assert result is True
        assert (Path(temp_storage_dir) / story_id).exists()
        
        # Verify data integrity
        restored_data = load_story_data(temp_storage_dir, story_id)
        assert restored_data == sample_story_data
    
    def test_restore_story_backup_invalid_file(self, temp_storage_dir):
        """Test restoring from invalid backup file."""
        # Create fake backup file
        fake_backup = Path(temp_storage_dir) / "fake_backup.zip"
        fake_backup.write_text("not a zip file")
        
        result = restore_story_backup(temp_storage_dir, str(fake_backup))
        
        assert result is False


class TestDatabaseManager:
    """Test DatabaseManager class."""
    
    def test_database_manager_init(self, temp_storage_dir):
        """Test DatabaseManager initialization."""
        db_manager = DatabaseManager(temp_storage_dir)
        
        assert db_manager.storage_path == temp_storage_dir
        assert hasattr(db_manager, 'connection')
    
    def test_database_manager_create_tables(self, db_manager):
        """Test creating database tables."""
        result = db_manager.create_tables()
        
        assert result is True
        
        # Check tables were created
        cursor = db_manager.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "stories" in tables
        assert "scenes" in tables
        assert "characters" in tables
    
    def test_database_manager_insert_story(self, db_manager, sample_story_data):
        """Test inserting story into database."""
        db_manager.create_tables()
        
        result = db_manager.insert_story(sample_story_data)
        
        assert result is True
        
        # Verify insertion
        story = db_manager.get_story(sample_story_data["id"])
        assert story is not None
        assert story["title"] == sample_story_data["meta"]["title"]
    
    def test_database_manager_update_story(self, db_manager, sample_story_data):
        """Test updating story in database."""
        db_manager.create_tables()
        db_manager.insert_story(sample_story_data)
        
        # Update story data
        updated_data = sample_story_data.copy()
        updated_data["meta"]["title"] = "Updated Title"
        
        result = db_manager.update_story(updated_data)
        
        assert result is True
        
        # Verify update
        story = db_manager.get_story(sample_story_data["id"])
        assert story["title"] == "Updated Title"
    
    def test_database_manager_delete_story(self, db_manager, sample_story_data):
        """Test deleting story from database."""
        db_manager.create_tables()
        db_manager.insert_story(sample_story_data)
        
        result = db_manager.delete_story(sample_story_data["id"])
        
        assert result is True
        
        # Verify deletion
        story = db_manager.get_story(sample_story_data["id"])
        assert story is None
    
    def test_database_manager_list_stories(self, db_manager, sample_story_data):
        """Test listing stories from database."""
        db_manager.create_tables()
        
        # Insert multiple stories
        for i in range(3):
            story_data = sample_story_data.copy()
            story_data["id"] = f"story_{i}"
            story_data["meta"]["title"] = f"Story {i}"
            db_manager.insert_story(story_data)
        
        stories = db_manager.list_stories()
        
        assert len(stories) == 3
        assert all("story_" in story["id"] for story in stories)
    
    def test_database_manager_search_stories(self, db_manager, sample_story_data):
        """Test searching stories in database."""
        db_manager.create_tables()
        
        # Insert test stories
        story1 = sample_story_data.copy()
        story1["id"] = "fantasy_story"
        story1["meta"]["title"] = "Fantasy Adventure"
        db_manager.insert_story(story1)
        
        story2 = sample_story_data.copy()
        story2["id"] = "sci_fi_story"
        story2["meta"]["title"] = "Space Opera"
        db_manager.insert_story(story2)
        
        # Search for fantasy stories
        results = db_manager.search_stories("fantasy")
        
        assert len(results) == 1
        assert results[0]["id"] == "fantasy_story"
    
    def test_database_manager_close(self, db_manager):
        """Test closing database connection."""
        result = db_manager.close()
        
        assert result is True
        
        # Connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            db_manager.connection.execute("SELECT 1")


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_save_story_data_permission_error(self, temp_storage_dir, sample_story_data):
        """Test handling permission errors during save."""
        story_id = "permission_test"
        
        # Mock a permission error
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = save_story_data(temp_storage_dir, story_id, sample_story_data)
        
        assert result is False
    
    def test_load_story_data_io_error(self, temp_storage_dir):
        """Test handling IO errors during load."""
        story_id = "io_error_test"
        
        # Mock an IO error
        with patch('builtins.open', side_effect=IOError("Disk error")):
            result = load_story_data(temp_storage_dir, story_id)
        
        assert result == {}
    
    def test_database_manager_connection_error(self, temp_storage_dir):
        """Test handling database connection errors."""
        # Use invalid path to trigger connection error
        invalid_path = "/invalid/path/that/does/not/exist"
        
        with pytest.raises(Exception):
            DatabaseManager(invalid_path)
    
    def test_database_manager_sql_error(self, db_manager):
        """Test handling SQL errors."""
        # Try to insert without creating tables first
        with pytest.raises(sqlite3.OperationalError):
            db_manager.connection.execute("INSERT INTO stories VALUES (?, ?)", ("test", "data"))


class TestPerformance:
    """Test performance and optimization."""
    
    def test_large_story_data_handling(self, temp_storage_dir):
        """Test handling large story data."""
        # Create large story data
        large_story = {
            "id": "large_story",
            "meta": {"title": "Large Story"},
            "characters": {},
            "world": {"locations": {}}
        }
        
        # Add many characters
        for i in range(1000):
            large_story["characters"][f"character_{i}"] = {
                "name": f"Character {i}",
                "personality": f"Personality {i}",
                "stats": {"strength": i % 10, "intelligence": (i + 1) % 10}
            }
        
        # Add many locations
        for i in range(500):
            large_story["world"]["locations"][f"location_{i}"] = {
                "name": f"Location {i}",
                "description": f"Description for location {i}"
            }
        
        # Test save and load
        result = save_story_data(temp_storage_dir, "large_story", large_story)
        assert result is True
        
        loaded_data = load_story_data(temp_storage_dir, "large_story")
        assert len(loaded_data["characters"]) == 1000
        assert len(loaded_data["world"]["locations"]) == 500
    
    def test_concurrent_access_simulation(self, temp_storage_dir, sample_story_data):
        """Test simulated concurrent access."""
        import threading
        import time
        
        results = []
        
        def save_story_worker(story_id):
            story_data = sample_story_data.copy()
            story_data["id"] = story_id
            result = save_story_data(temp_storage_dir, story_id, story_data)
            results.append(result)
            time.sleep(0.1)  # Simulate processing time
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=save_story_worker, args=[f"concurrent_story_{i}"])
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check all operations succeeded
        assert all(results)
        assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__])

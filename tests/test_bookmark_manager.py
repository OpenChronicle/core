"""
Test suite for Bookmark Manager

Tests bookmark creation, organization, and navigation functionality.
"""

import pytest
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from core.bookmark_manager import (
    BookmarkManager,
    Bookmark,
    create_bookmark,
    get_bookmarks,
    organize_bookmarks,
    export_bookmarks,
    search_bookmarks,
    validate_bookmark_data
)


@pytest.fixture
def temp_story_dir():
    """Create temporary story directory for testing."""
    temp_dir = tempfile.mkdtemp()
    story_path = Path(temp_dir) / "test_story"
    story_path.mkdir(parents=True)
    
    # Create bookmarks directory
    bookmarks_dir = story_path / "bookmarks"
    bookmarks_dir.mkdir()
    
    yield str(story_path)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_bookmark_data():
    """Sample bookmark data for testing."""
    return {
        "bookmark_id": "bookmark_001",
        "title": "Alice meets the wizard",
        "description": "Important scene where Alice first encounters magical guidance",
        "scene_id": "scene_015",
        "timestamp": "2024-01-01T14:30:00Z",
        "tags": ["character_introduction", "magic", "important"],
        "category": "characters",
        "notes": "This scene establishes Alice's relationship with magic",
        "favorite": True,
        "metadata": {
            "word_count": 450,
            "characters_involved": ["Alice", "Wizard_Gandor"],
            "location": "wizard_tower",
            "mood": "mystical"
        }
    }


@pytest.fixture
def bookmark_manager(temp_story_dir):
    """Create BookmarkManager instance for testing."""
    return BookmarkManager(temp_story_dir)


class TestBookmark:
    """Test Bookmark data structure."""
    
    def test_bookmark_creation(self, sample_bookmark_data):
        """Test creating Bookmark from data."""
        bookmark = Bookmark.from_dict(sample_bookmark_data)
        
        assert bookmark.bookmark_id == "bookmark_001"
        assert bookmark.title == "Alice meets the wizard"
        assert "magic" in bookmark.tags
        assert bookmark.favorite is True
    
    def test_bookmark_to_dict(self, sample_bookmark_data):
        """Test converting Bookmark to dictionary."""
        bookmark = Bookmark.from_dict(sample_bookmark_data)
        bookmark_dict = bookmark.to_dict()
        
        assert bookmark_dict["bookmark_id"] == sample_bookmark_data["bookmark_id"]
        assert bookmark_dict["title"] == sample_bookmark_data["title"]
        assert bookmark_dict["tags"] == sample_bookmark_data["tags"]
    
    def test_bookmark_validation(self):
        """Test Bookmark validation."""
        valid_data = {
            "bookmark_id": "test_bookmark",
            "title": "Test Bookmark",
            "scene_id": "test_scene",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        bookmark = Bookmark.from_dict(valid_data)
        assert bookmark.bookmark_id == "test_bookmark"
        
        # Test with missing required field
        invalid_data = {
            "bookmark_id": "invalid_bookmark",
            # Missing title
            "scene_id": "test_scene"
        }
        
        with pytest.raises(KeyError):
            Bookmark.from_dict(invalid_data)
    
    def test_bookmark_defaults(self):
        """Test Bookmark default values."""
        minimal_data = {
            "bookmark_id": "minimal_bookmark",
            "title": "Minimal Test",
            "scene_id": "test_scene",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        bookmark = Bookmark.from_dict(minimal_data)
        
        assert bookmark.description == ""
        assert bookmark.tags == []
        assert bookmark.favorite is False
        assert bookmark.metadata == {}
    
    def test_bookmark_ordering(self, sample_bookmark_data):
        """Test Bookmark ordering by timestamp."""
        bookmarks_data = [
            sample_bookmark_data,
            {
                "bookmark_id": "bookmark_002",
                "title": "Second bookmark", 
                "scene_id": "scene_016",
                "timestamp": "2024-01-01T15:00:00Z"
            },
            {
                "bookmark_id": "bookmark_003",
                "title": "Third bookmark",
                "scene_id": "scene_017", 
                "timestamp": "2024-01-01T13:00:00Z"
            }
        ]
        
        bookmarks = [Bookmark.from_dict(data) for data in bookmarks_data]
        sorted_bookmarks = sorted(bookmarks, key=lambda b: b.timestamp)
        
        assert sorted_bookmarks[0].bookmark_id == "bookmark_003"  # 13:00
        assert sorted_bookmarks[1].bookmark_id == "bookmark_001"  # 14:30
        assert sorted_bookmarks[2].bookmark_id == "bookmark_002"  # 15:00


class TestBookmarkManager:
    """Test BookmarkManager functionality."""
    
    def test_bookmark_manager_init(self, temp_story_dir):
        """Test BookmarkManager initialization."""
        manager = BookmarkManager(temp_story_dir)
        
        assert manager.story_path == temp_story_dir
        assert manager.bookmarks_dir.exists()
        assert hasattr(manager, 'bookmarks')
    
    def test_create_bookmark(self, bookmark_manager, sample_bookmark_data):
        """Test creating a bookmark."""
        result = bookmark_manager.create_bookmark(sample_bookmark_data)
        
        assert result is True
        assert len(bookmark_manager.bookmarks) == 1
        
        # Verify bookmark file was created
        bookmark_file = bookmark_manager.bookmarks_dir / "bookmark_001.json"
        assert bookmark_file.exists()
        
        # Check content
        with open(bookmark_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["bookmark_id"] == "bookmark_001"
        assert saved_data["title"] == sample_bookmark_data["title"]
    
    def test_create_bookmark_auto_id(self, bookmark_manager):
        """Test creating bookmark with auto-generated ID."""
        bookmark_data = {
            "title": "Auto ID Bookmark",
            "scene_id": "auto_scene",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        bookmark_id = bookmark_manager.create_bookmark(bookmark_data, auto_id=True)
        
        assert bookmark_id is not None
        assert len(bookmark_manager.bookmarks) == 1
    
    def test_get_bookmark(self, bookmark_manager, sample_bookmark_data):
        """Test getting specific bookmark."""
        bookmark_manager.create_bookmark(sample_bookmark_data)
        
        bookmark = bookmark_manager.get_bookmark("bookmark_001")
        
        assert bookmark is not None
        assert bookmark.title == "Alice meets the wizard"
    
    def test_get_bookmark_not_found(self, bookmark_manager):
        """Test getting non-existent bookmark."""
        bookmark = bookmark_manager.get_bookmark("nonexistent_bookmark")
        
        assert bookmark is None
    
    def test_update_bookmark(self, bookmark_manager, sample_bookmark_data):
        """Test updating existing bookmark."""
        bookmark_manager.create_bookmark(sample_bookmark_data)
        
        updated_data = {
            "title": "Updated: Alice meets the wizard",
            "description": "Updated description with more details"
        }
        
        result = bookmark_manager.update_bookmark("bookmark_001", updated_data)
        
        assert result is True
        
        bookmark = bookmark_manager.get_bookmark("bookmark_001")
        assert bookmark.title == "Updated: Alice meets the wizard"
        assert "Updated description" in bookmark.description
    
    def test_delete_bookmark(self, bookmark_manager, sample_bookmark_data):
        """Test deleting a bookmark."""
        bookmark_manager.create_bookmark(sample_bookmark_data)
        assert len(bookmark_manager.bookmarks) == 1
        
        result = bookmark_manager.delete_bookmark("bookmark_001")
        
        assert result is True
        assert len(bookmark_manager.bookmarks) == 0
        
        # Verify file was deleted
        bookmark_file = bookmark_manager.bookmarks_dir / "bookmark_001.json"
        assert not bookmark_file.exists()
    
    def test_list_bookmarks(self, bookmark_manager, sample_bookmark_data):
        """Test listing all bookmarks."""
        # Create multiple bookmarks
        for i in range(3):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["title"] = f"Bookmark {i}"
            bookmark_manager.create_bookmark(bookmark_data)
        
        bookmarks = bookmark_manager.list_bookmarks()
        
        assert len(bookmarks) == 3
        assert all(isinstance(bookmark, Bookmark) for bookmark in bookmarks)
    
    def test_get_bookmarks_by_category(self, bookmark_manager, sample_bookmark_data):
        """Test getting bookmarks by category."""
        categories = ["characters", "locations", "plot"]
        
        for i, category in enumerate(categories):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["category"] = category
            bookmark_manager.create_bookmark(bookmark_data)
        
        character_bookmarks = bookmark_manager.get_bookmarks_by_category("characters")
        location_bookmarks = bookmark_manager.get_bookmarks_by_category("locations")
        
        assert len(character_bookmarks) == 1
        assert len(location_bookmarks) == 1
    
    def test_get_bookmarks_by_tags(self, bookmark_manager, sample_bookmark_data):
        """Test getting bookmarks by tags."""
        # Create bookmarks with different tags
        bookmark_data_1 = sample_bookmark_data.copy()
        bookmark_data_1["bookmark_id"] = "bookmark_001"
        bookmark_data_1["tags"] = ["magic", "important"]
        
        bookmark_data_2 = sample_bookmark_data.copy()
        bookmark_data_2["bookmark_id"] = "bookmark_002"
        bookmark_data_2["tags"] = ["combat", "important"]
        
        bookmark_data_3 = sample_bookmark_data.copy()
        bookmark_data_3["bookmark_id"] = "bookmark_003"
        bookmark_data_3["tags"] = ["dialogue"]
        
        for data in [bookmark_data_1, bookmark_data_2, bookmark_data_3]:
            bookmark_manager.create_bookmark(data)
        
        magic_bookmarks = bookmark_manager.get_bookmarks_by_tags(["magic"])
        important_bookmarks = bookmark_manager.get_bookmarks_by_tags(["important"])
        
        assert len(magic_bookmarks) == 1
        assert len(important_bookmarks) == 2
    
    def test_get_favorite_bookmarks(self, bookmark_manager, sample_bookmark_data):
        """Test getting favorite bookmarks."""
        # Create mix of favorite and non-favorite bookmarks
        for i in range(4):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["favorite"] = i % 2 == 0  # Every other one is favorite
            bookmark_manager.create_bookmark(bookmark_data)
        
        favorites = bookmark_manager.get_favorite_bookmarks()
        
        assert len(favorites) == 2  # bookmarks 0 and 2
        assert all(bookmark.favorite for bookmark in favorites)


class TestBookmarkSearch:
    """Test bookmark search functionality."""
    
    def test_search_bookmarks_by_title(self, bookmark_manager, sample_bookmark_data):
        """Test searching bookmarks by title."""
        # Create bookmarks with different titles
        titles = ["Alice meets wizard", "Bob's great adventure", "Charlie finds treasure"]
        
        for i, title in enumerate(titles):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["title"] = title
            bookmark_manager.create_bookmark(bookmark_data)
        
        alice_bookmarks = bookmark_manager.search_bookmarks("Alice")
        adventure_bookmarks = bookmark_manager.search_bookmarks("adventure")
        
        assert len(alice_bookmarks) == 1
        assert len(adventure_bookmarks) == 1
    
    def test_search_bookmarks_by_description(self, bookmark_manager, sample_bookmark_data):
        """Test searching bookmarks by description."""
        bookmark_data = sample_bookmark_data.copy()
        bookmark_data["description"] = "Scene with magical elements and character development"
        bookmark_manager.create_bookmark(bookmark_data)
        
        magic_search = bookmark_manager.search_bookmarks("magical")
        character_search = bookmark_manager.search_bookmarks("character development")
        
        assert len(magic_search) == 1
        assert len(character_search) == 1
    
    def test_search_bookmarks_by_notes(self, bookmark_manager, sample_bookmark_data):
        """Test searching bookmarks by notes."""
        bookmark_data = sample_bookmark_data.copy()
        bookmark_data["notes"] = "Remember to expand this scene in revision"
        bookmark_manager.create_bookmark(bookmark_data)
        
        revision_search = bookmark_manager.search_bookmarks("revision")
        expand_search = bookmark_manager.search_bookmarks("expand")
        
        assert len(revision_search) == 1
        assert len(expand_search) == 1
    
    def test_advanced_search(self, bookmark_manager, sample_bookmark_data):
        """Test advanced bookmark search with filters."""
        # Create bookmarks with various attributes
        for i in range(5):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["category"] = "characters" if i < 3 else "locations"
            bookmark_data["favorite"] = i % 2 == 0
            bookmark_data["tags"] = ["important"] if i < 2 else ["minor"]
            bookmark_manager.create_bookmark(bookmark_data)
        
        # Search with multiple filters
        results = bookmark_manager.advanced_search(
            category="characters",
            favorite=True,
            tags=["important"]
        )
        
        assert len(results) == 1  # Only bookmark_000 matches all criteria


class TestBookmarkOrganization:
    """Test bookmark organization functionality."""
    
    def test_organize_bookmarks_by_category(self, bookmark_manager, sample_bookmark_data):
        """Test organizing bookmarks by category."""
        categories = ["characters", "locations", "plot", "worldbuilding"]
        
        for i, category in enumerate(categories):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["category"] = category
            bookmark_manager.create_bookmark(bookmark_data)
        
        organized = bookmark_manager.organize_by_category()
        
        assert isinstance(organized, dict)
        assert len(organized) == 4
        assert all(category in organized for category in categories)
        assert all(len(organized[category]) == 1 for category in categories)
    
    def test_organize_bookmarks_by_timeline(self, bookmark_manager, sample_bookmark_data):
        """Test organizing bookmarks by timeline."""
        base_time = datetime.fromisoformat("2024-01-01T12:00:00")
        
        for i in range(5):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            timestamp = base_time + timedelta(hours=i*2)
            bookmark_data["timestamp"] = timestamp.isoformat() + "Z"
            bookmark_manager.create_bookmark(bookmark_data)
        
        timeline_organized = bookmark_manager.organize_by_timeline()
        
        assert isinstance(timeline_organized, list)
        assert len(timeline_organized) == 5
        # Should be sorted by timestamp
        assert timeline_organized[0].bookmark_id == "bookmark_000"
        assert timeline_organized[-1].bookmark_id == "bookmark_004"
    
    def test_organize_bookmarks_by_scene_sequence(self, bookmark_manager, sample_bookmark_data):
        """Test organizing bookmarks by scene sequence."""
        scene_ids = ["scene_005", "scene_012", "scene_008", "scene_020"]
        
        for i, scene_id in enumerate(scene_ids):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["scene_id"] = scene_id
            bookmark_manager.create_bookmark(bookmark_data)
        
        scene_organized = bookmark_manager.organize_by_scene_sequence()
        
        assert isinstance(scene_organized, list)
        assert len(scene_organized) == 4
        # Should be sorted by scene_id numerically
        assert scene_organized[0].scene_id == "scene_005"
        assert scene_organized[-1].scene_id == "scene_020"


class TestBookmarkExport:
    """Test bookmark export functionality."""
    
    def test_export_bookmarks_json(self, bookmark_manager, sample_bookmark_data):
        """Test exporting bookmarks as JSON."""
        # Create multiple bookmarks
        for i in range(3):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_manager.create_bookmark(bookmark_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name
        
        result = bookmark_manager.export_bookmarks(export_file, format="json")
        
        assert result is True
        
        # Verify export content
        with open(export_file, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 3
        assert exported_data[0]["bookmark_id"] == "bookmark_000"
        
        # Cleanup
        Path(export_file).unlink()
    
    def test_export_bookmarks_csv(self, bookmark_manager, sample_bookmark_data):
        """Test exporting bookmarks as CSV."""
        bookmark_manager.create_bookmark(sample_bookmark_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            export_file = f.name
        
        result = bookmark_manager.export_bookmarks(export_file, format="csv")
        
        assert result is True
        
        # Verify export content
        with open(export_file, 'r') as f:
            content = f.read()
        
        assert "bookmark_001" in content
        assert "Alice meets the wizard" in content
        
        # Cleanup
        Path(export_file).unlink()
    
    def test_export_bookmarks_filtered(self, bookmark_manager, sample_bookmark_data):
        """Test exporting filtered bookmarks."""
        # Create bookmarks with different categories
        categories = ["characters", "locations"]
        
        for i, category in enumerate(categories):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["category"] = category
            bookmark_manager.create_bookmark(bookmark_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name
        
        result = bookmark_manager.export_bookmarks(
            export_file, 
            format="json",
            category_filter="characters"
        )
        
        assert result is True
        
        with open(export_file, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 1
        assert exported_data[0]["category"] == "characters"
        
        # Cleanup
        Path(export_file).unlink()


class TestBookmarkFunctions:
    """Test standalone bookmark functions."""
    
    def test_create_bookmark_function(self, temp_story_dir, sample_bookmark_data):
        """Test standalone create_bookmark function."""
        result = create_bookmark(temp_story_dir, sample_bookmark_data)
        
        assert result is True
        
        # Verify bookmark was created
        bookmark_file = Path(temp_story_dir) / "bookmarks" / "bookmark_001.json"
        assert bookmark_file.exists()
    
    def test_get_bookmarks_function(self, temp_story_dir, sample_bookmark_data):
        """Test standalone get_bookmarks function."""
        create_bookmark(temp_story_dir, sample_bookmark_data)
        
        bookmarks = get_bookmarks(temp_story_dir)
        
        assert len(bookmarks) == 1
        assert bookmarks[0]["bookmark_id"] == "bookmark_001"
    
    def test_organize_bookmarks_function(self, temp_story_dir, sample_bookmark_data):
        """Test standalone organize_bookmarks function."""
        # Create multiple bookmarks
        for i in range(3):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["category"] = f"category_{i}"
            create_bookmark(temp_story_dir, bookmark_data)
        
        organized = organize_bookmarks(temp_story_dir, by="category")
        
        assert isinstance(organized, dict)
        assert len(organized) == 3
    
    def test_search_bookmarks_function(self, temp_story_dir, sample_bookmark_data):
        """Test standalone search_bookmarks function."""
        create_bookmark(temp_story_dir, sample_bookmark_data)
        
        results = search_bookmarks(temp_story_dir, "wizard")
        
        assert len(results) == 1
        assert results[0]["title"] == "Alice meets the wizard"
    
    def test_export_bookmarks_function(self, temp_story_dir, sample_bookmark_data):
        """Test standalone export_bookmarks function."""
        create_bookmark(temp_story_dir, sample_bookmark_data)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name
        
        result = export_bookmarks(temp_story_dir, export_file)
        
        assert result is True
        assert Path(export_file).exists()
        
        # Cleanup
        Path(export_file).unlink()
    
    def test_validate_bookmark_data_valid(self, sample_bookmark_data):
        """Test bookmark data validation with valid data."""
        result = validate_bookmark_data(sample_bookmark_data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_bookmark_data_invalid(self):
        """Test bookmark data validation with invalid data."""
        invalid_data = {
            "bookmark_id": "test_bookmark",
            # Missing required fields
        }
        
        result = validate_bookmark_data(invalid_data)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestBookmarkAnalytics:
    """Test bookmark analytics functionality."""
    
    def test_bookmark_usage_statistics(self, bookmark_manager, sample_bookmark_data):
        """Test bookmark usage statistics."""
        # Create bookmarks with different attributes
        categories = ["characters", "locations", "plot"]
        
        for i in range(9):  # 3 per category
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["category"] = categories[i % 3]
            bookmark_data["favorite"] = i % 2 == 0
            bookmark_manager.create_bookmark(bookmark_data)
        
        stats = bookmark_manager.get_statistics()
        
        assert isinstance(stats, dict)
        assert "total_bookmarks" in stats
        assert "bookmarks_by_category" in stats
        assert "favorite_count" in stats
        assert stats["total_bookmarks"] == 9
        assert stats["favorite_count"] == 5  # Every other one
    
    def test_bookmark_trends_analysis(self, bookmark_manager, sample_bookmark_data):
        """Test bookmark trends analysis."""
        base_time = datetime.fromisoformat("2024-01-01T12:00:00")
        
        # Create bookmarks over time
        for i in range(10):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            timestamp = base_time + timedelta(days=i)
            bookmark_data["timestamp"] = timestamp.isoformat() + "Z"
            bookmark_manager.create_bookmark(bookmark_data)
        
        trends = bookmark_manager.analyze_trends()
        
        assert isinstance(trends, dict)
        assert "bookmarks_per_day" in trends
        assert "creation_frequency" in trends
    
    def test_bookmark_tag_analysis(self, bookmark_manager, sample_bookmark_data):
        """Test tag usage analysis."""
        tag_sets = [
            ["important", "character"],
            ["location", "world"],
            ["important", "plot"], 
            ["character", "development"],
            ["important", "world"]
        ]
        
        for i, tags in enumerate(tag_sets):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"bookmark_{i:03d}"
            bookmark_data["tags"] = tags
            bookmark_manager.create_bookmark(bookmark_data)
        
        tag_analysis = bookmark_manager.analyze_tags()
        
        assert isinstance(tag_analysis, dict)
        assert "tag_frequency" in tag_analysis
        assert "most_used_tags" in tag_analysis
        assert tag_analysis["tag_frequency"]["important"] == 3


class TestBookmarkIntegration:
    """Test bookmark integration with other systems."""
    
    def test_bookmark_scene_integration(self, bookmark_manager):
        """Test bookmark integration with scene data."""
        scene_data = {
            "scene_id": "scene_025",
            "timestamp": "2024-01-01T15:00:00Z", 
            "user_input": "Alice discovers ancient ruins",
            "ai_response": "The ruins reveal secrets of the past",
            "characters_involved": ["Alice"],
            "location": "ancient_ruins"
        }
        
        bookmark_id = bookmark_manager.create_scene_bookmark(
            scene_data,
            title="Discovery of Ancient Ruins",
            tags=["discovery", "worldbuilding"]
        )
        
        assert bookmark_id is not None
        bookmark = bookmark_manager.get_bookmark(bookmark_id)
        assert bookmark.scene_id == "scene_025"
        assert "discovery" in bookmark.tags
    
    def test_bookmark_memory_integration(self, bookmark_manager, sample_bookmark_data):
        """Test bookmark integration with memory system."""
        bookmark_manager.create_bookmark(sample_bookmark_data)
        
        # Mock memory integration
        with patch('core.bookmark_manager.load_memory') as mock_load_memory:
            mock_load_memory.return_value = {
                "characters": {"Alice": {"current_state": {"location": "wizard_tower"}}}
            }
            
            context_bookmarks = bookmark_manager.get_contextual_bookmarks("scene_015")
        
        assert isinstance(context_bookmarks, list)
        mock_load_memory.assert_called()
    
    def test_bookmark_timeline_integration(self, bookmark_manager, sample_bookmark_data):
        """Test bookmark integration with timeline."""
        # Create bookmarks across timeline
        base_time = datetime.fromisoformat("2024-01-01T08:00:00")
        
        for i in range(5):
            bookmark_data = sample_bookmark_data.copy()
            bookmark_data["bookmark_id"] = f"timeline_bookmark_{i:03d}"
            timestamp = base_time + timedelta(hours=i*2)
            bookmark_data["timestamp"] = timestamp.isoformat() + "Z"
            bookmark_manager.create_bookmark(bookmark_data)
        
        timeline_view = bookmark_manager.get_timeline_view()
        
        assert isinstance(timeline_view, list)
        assert len(timeline_view) == 5
        # Should be chronologically ordered
        assert timeline_view[0].bookmark_id == "timeline_bookmark_000"


class TestErrorHandling:
    """Test error handling in bookmark operations."""
    
    def test_corrupted_bookmark_file(self, bookmark_manager):
        """Test handling corrupted bookmark files."""
        # Create corrupted bookmark file
        corrupted_file = bookmark_manager.bookmarks_dir / "corrupted_bookmark.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json content")
        
        # Should handle gracefully
        bookmark = bookmark_manager.get_bookmark("corrupted_bookmark")
        assert bookmark is None
    
    def test_duplicate_bookmark_id(self, bookmark_manager, sample_bookmark_data):
        """Test handling duplicate bookmark IDs."""
        # Create first bookmark
        result1 = bookmark_manager.create_bookmark(sample_bookmark_data)
        assert result1 is True
        
        # Try to create bookmark with same ID
        result2 = bookmark_manager.create_bookmark(sample_bookmark_data, allow_duplicate=False)
        assert result2 is False
        
        # With overwrite enabled
        updated_data = sample_bookmark_data.copy()
        updated_data["title"] = "Updated Title"
        result3 = bookmark_manager.create_bookmark(updated_data, allow_duplicate=True)
        assert result3 is True
    
    def test_insufficient_permissions(self, bookmark_manager, sample_bookmark_data):
        """Test handling permission errors."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = bookmark_manager.create_bookmark(sample_bookmark_data)
        
        assert result is False
    
    def test_disk_space_error(self, bookmark_manager, sample_bookmark_data):
        """Test handling disk space errors."""
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            result = bookmark_manager.create_bookmark(sample_bookmark_data)
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])

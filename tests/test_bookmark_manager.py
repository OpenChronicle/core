"""
Test suite for BookmarkManager.
Tests bookmark creation, management, and navigation functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from core.management_systems import BookmarkManager


@pytest.fixture
def temp_story_id():
    """Create temporary story ID for testing."""
    return "test_story_" + str(datetime.now().timestamp()).replace('.', '_')


@pytest.fixture
def bookmark_manager(temp_story_id):
    """Create BookmarkManager instance for testing."""
    # Mock the database initialization to avoid file system dependencies
    with patch('core.management_systems.bookmark.bookmark_manager.init_database'):
        manager = BookmarkManager(temp_story_id)
        return manager


@pytest.fixture
def sample_bookmark_data():
    """Sample bookmark data for testing."""
    return {
        "scene_id": "scene_001",
        "label": "The Wizard's Tower",
        "description": "Important scene where the wizard appears",
        "bookmark_type": "user",
        "metadata": {"chapter": 1, "importance": "high"}
    }


class TestBookmarkManagerInitialization:
    """Test BookmarkManager initialization."""
    
    def test_init_with_story_id(self, temp_story_id):
        """Test BookmarkManager initialization with story ID."""
        with patch('core.bookmark_manager.init_database') as mock_init:
            manager = BookmarkManager(temp_story_id)
            
            assert manager.story_id == temp_story_id
            mock_init.assert_called_once_with(temp_story_id)


class TestBookmarkCreation:
    """Test bookmark creation functionality."""
    
    def test_create_bookmark_success(self, bookmark_manager, sample_bookmark_data):
        """Test successful bookmark creation."""
        with patch('core.bookmark_manager.execute_query', return_value=[]), \
             patch('core.bookmark_manager.execute_insert', return_value=123):
            
            bookmark_id = bookmark_manager.create_bookmark(
                scene_id=sample_bookmark_data["scene_id"],
                label=sample_bookmark_data["label"],
                description=sample_bookmark_data["description"],
                bookmark_type=sample_bookmark_data["bookmark_type"],
                metadata=sample_bookmark_data["metadata"]
            )
            
            assert bookmark_id == 123
    
    def test_create_bookmark_invalid_type(self, bookmark_manager):
        """Test bookmark creation with invalid type."""
        with pytest.raises(ValueError, match="Invalid bookmark type"):
            bookmark_manager.create_bookmark(
                scene_id="scene_001",
                label="Test Bookmark",
                bookmark_type="invalid_type"
            )
    
    def test_create_bookmark_duplicate_label(self, bookmark_manager):
        """Test bookmark creation with duplicate label for same scene."""
        # Mock existing bookmark
        with patch('core.bookmark_manager.execute_query', return_value=[{"id": 1}]):
            with pytest.raises(ValueError, match="Bookmark with label .* already exists"):
                bookmark_manager.create_bookmark(
                    scene_id="scene_001",
                    label="Existing Label"
                )
    
    def test_create_bookmark_minimal_data(self, bookmark_manager):
        """Test bookmark creation with minimal required data."""
        with patch('core.bookmark_manager.execute_query', return_value=[]), \
             patch('core.bookmark_manager.execute_insert', return_value=456):
            
            bookmark_id = bookmark_manager.create_bookmark(
                scene_id="scene_002",
                label="Simple Bookmark"
            )
            
            assert bookmark_id == 456


class TestBookmarkRetrieval:
    """Test bookmark retrieval functionality."""
    
    def test_get_bookmark_success(self, bookmark_manager):
        """Test successful bookmark retrieval."""
        mock_bookmark = {
            "id": 1,
            "story_id": "test_story",
            "scene_id": "scene_001",
            "label": "Test Bookmark",
            "description": "Test description",
            "bookmark_type": "user",
            "created_at": "2025-07-24T12:00:00Z",
            "metadata": "{}"
        }
        
        with patch('core.bookmark_manager.execute_query', return_value=[mock_bookmark]):
            bookmark = bookmark_manager.get_bookmark(1)
            
            assert bookmark is not None
            assert bookmark["id"] == 1
            assert bookmark["label"] == "Test Bookmark"
    
    def test_get_bookmark_not_found(self, bookmark_manager):
        """Test bookmark retrieval when bookmark doesn't exist."""
        with patch('core.bookmark_manager.execute_query', return_value=[]):
            bookmark = bookmark_manager.get_bookmark(999)
            
            assert bookmark is None
    
    def test_list_bookmarks_all(self, bookmark_manager):
        """Test listing all bookmarks."""
        mock_bookmarks = [
            {
                "id": 1, 
                "story_id": "test_story",
                "scene_id": "scene_001",
                "label": "Bookmark 1", 
                "description": "Test description 1",
                "bookmark_type": "user",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": "{}"
            },
            {
                "id": 2, 
                "story_id": "test_story",
                "scene_id": "scene_002",
                "label": "Bookmark 2", 
                "description": "Test description 2",
                "bookmark_type": "auto",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": "{}"
            }
        ]
        
        with patch('core.bookmark_manager.execute_query', return_value=mock_bookmarks):
            bookmarks = bookmark_manager.list_bookmarks()
            
            assert len(bookmarks) == 2
            assert bookmarks[0]["label"] == "Bookmark 1"
    
    def test_list_bookmarks_by_type(self, bookmark_manager):
        """Test listing bookmarks filtered by type."""
        mock_bookmarks = [
            {
                "id": 1, 
                "story_id": "test_story",
                "scene_id": "scene_001",
                "label": "User Bookmark", 
                "description": "Test description",
                "bookmark_type": "user",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": "{}"
            }
        ]
        
        with patch('core.bookmark_manager.execute_query', return_value=mock_bookmarks):
            bookmarks = bookmark_manager.list_bookmarks(bookmark_type="user")
            
            assert len(bookmarks) == 1
            assert bookmarks[0]["bookmark_type"] == "user"
    
    def test_list_bookmarks_by_scene(self, bookmark_manager):
        """Test listing bookmarks filtered by scene."""
        mock_bookmarks = [
            {
                "id": 1, 
                "story_id": "test_story",
                "scene_id": "scene_001",
                "label": "Scene Bookmark", 
                "description": "Test description",
                "bookmark_type": "user",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": "{}"
            }
        ]
        
        with patch('core.bookmark_manager.execute_query', return_value=mock_bookmarks):
            bookmarks = bookmark_manager.list_bookmarks(scene_id="scene_001")
            
            assert len(bookmarks) == 1
            assert bookmarks[0]["scene_id"] == "scene_001"


class TestBookmarkUpdate:
    """Test bookmark update functionality."""
    
    def test_update_bookmark_success(self, bookmark_manager):
        """Test successful bookmark update."""
        # Mock the get_bookmark call first
        mock_bookmark = {
            "id": 1,
            "story_id": "test_story",
            "scene_id": "scene_001",
            "label": "Original Label",
            "description": "Original description",
            "bookmark_type": "user",
            "created_at": "2025-07-24T12:00:00Z",
            "metadata": {}
        }
        
        with patch.object(bookmark_manager, 'get_bookmark', return_value=mock_bookmark), \
             patch('core.bookmark_manager.execute_update', return_value=1):
            result = bookmark_manager.update_bookmark(
                bookmark_id=1,
                label="Updated Label",
                description="Updated description"
            )
            
            assert result is True
    
    def test_update_bookmark_not_found(self, bookmark_manager):
        """Test updating non-existent bookmark."""
        with patch('core.bookmark_manager.execute_update', return_value=0):
            result = bookmark_manager.update_bookmark(
                bookmark_id=999,
                label="Updated Label"
            )
            
            assert result is False


class TestBookmarkDeletion:
    """Test bookmark deletion functionality."""
    
    def test_delete_bookmark_success(self, bookmark_manager):
        """Test successful bookmark deletion."""
        with patch('core.bookmark_manager.execute_update', return_value=1):
            result = bookmark_manager.delete_bookmark(1)
            
            assert result is True
    
    def test_delete_bookmark_not_found(self, bookmark_manager):
        """Test deleting non-existent bookmark."""
        with patch('core.bookmark_manager.execute_update', return_value=0):
            result = bookmark_manager.delete_bookmark(999)
            
            assert result is False


class TestBookmarkSearch:
    """Test bookmark search functionality."""
    
    def test_search_bookmarks_by_text(self, bookmark_manager):
        """Test searching bookmarks by text query."""
        mock_results = [
            {
                "id": 1, 
                "story_id": "test_story",
                "scene_id": "scene_001",
                "label": "Wizard Tower", 
                "description": "Important wizard scene",
                "bookmark_type": "user",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": "{}"
            }
        ]
        
        with patch('core.bookmark_manager.execute_query', return_value=mock_results):
            results = bookmark_manager.search_bookmarks("wizard")
            
            assert len(results) == 1
            assert "wizard" in results[0]["label"].lower()


class TestChapterBookmarks:
    """Test chapter-specific bookmark functionality."""
    
    def test_auto_create_chapter_bookmark(self, bookmark_manager):
        """Test automatic chapter bookmark creation."""
        with patch('core.bookmark_manager.execute_query', return_value=[]), \
             patch('core.bookmark_manager.execute_insert', return_value=789):
            
            bookmark_id = bookmark_manager.auto_create_chapter_bookmark(
                scene_id="scene_chapter_1",
                chapter_title="The Beginning",
                chapter_level=1
            )
            
            assert bookmark_id == 789
    
    def test_get_chapter_bookmarks(self, bookmark_manager):
        """Test retrieving chapter bookmarks."""
        mock_chapters = [
            {
                "id": 1, 
                "story_id": "test_story",
                "scene_id": "scene_001",
                "label": "Chapter 1", 
                "description": "First chapter",
                "bookmark_type": "chapter",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": "{}"
            }
        ]
        
        with patch('core.bookmark_manager.execute_query', return_value=mock_chapters):
            chapters = bookmark_manager.get_chapter_bookmarks()
            
            assert len(chapters) == 1
            assert chapters[0]["bookmark_type"] == "chapter"
    
    def test_get_chapter_structure(self, bookmark_manager):
        """Test getting chapter structure."""
        mock_chapters = [
            {
                "id": 1,
                "story_id": "test_story",
                "scene_id": "scene_001",
                "label": "Chapter 1",
                "description": "First chapter",
                "bookmark_type": "chapter",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": {"chapter_level": 1}
            },
            {
                "id": 2,
                "story_id": "test_story",
                "scene_id": "scene_002",
                "label": "Scene A",
                "description": "First scene",
                "bookmark_type": "chapter",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": {"chapter_level": 1}
            },
            {
                "id": 3,
                "story_id": "test_story",
                "scene_id": "scene_003",
                "label": "Chapter 2",
                "description": "Second chapter",
                "bookmark_type": "chapter",
                "created_at": "2025-07-24T12:00:00Z",
                "metadata": {"chapter_level": 2}
            }
        ]
        
        with patch.object(bookmark_manager, 'get_chapter_bookmarks', return_value=mock_chapters):
            structure = bookmark_manager.get_chapter_structure()
            
            assert isinstance(structure, dict)
            assert 1 in structure
            assert 2 in structure
            assert len(structure[1]) == 2  # Chapter 1 has 2 entries
            assert len(structure[2]) == 1  # Chapter 2 has 1 entry


class TestBookmarkStats:
    """Test bookmark statistics functionality."""
    
    def test_get_stats(self, bookmark_manager):
        """Test getting bookmark statistics."""
        # Mock the three different query calls
        def mock_execute_query(story_id, query, params):
            if "COUNT(*) as count" in query and "GROUP BY" not in query:
                return [{"count": 10}]
            elif "GROUP BY bookmark_type" in query:
                return [
                    {"bookmark_type": "user", "count": 5},
                    {"bookmark_type": "chapter", "count": 3},
                    {"bookmark_type": "auto", "count": 2}
                ]
            elif "ORDER BY created_at DESC" in query:
                return [
                    {"id": 1, "label": "Recent 1", "bookmark_type": "user", "created_at": "2025-07-24T12:00:00Z"}
                ]
            return []
        
        with patch('core.bookmark_manager.execute_query', side_effect=mock_execute_query):
            stats = bookmark_manager.get_stats()
            
            assert "total_bookmarks" in stats
            assert "by_type" in stats
            assert stats["total_bookmarks"] == 10
            assert stats["by_type"]["user"] == 5
            assert stats["by_type"]["chapter"] == 3
            assert stats["by_type"]["auto"] == 2


class TestBookmarkValidation:
    """Test bookmark data validation."""
    
    def test_valid_bookmark_types(self, bookmark_manager):
        """Test that valid bookmark types are accepted."""
        valid_types = ["user", "auto", "chapter", "system"]
        
        for bookmark_type in valid_types:
            with patch('core.bookmark_manager.execute_query', return_value=[]), \
                 patch('core.bookmark_manager.execute_insert', return_value=1):
                
                # Should not raise an exception
                bookmark_manager.create_bookmark(
                    scene_id="scene_test",
                    label=f"Test {bookmark_type}",
                    bookmark_type=bookmark_type
                )


if __name__ == "__main__":
    pytest.main([__file__])

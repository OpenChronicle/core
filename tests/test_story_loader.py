"""
Test suite for Story Loader

Tests story loading, validation, and initialization functionality.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from core.story_loader import (
    load_story,
    load_story_data,
    validate_story_structure,
    initialize_story,
    get_available_stories,
    create_story_from_template,
    StoryLoader,
    StoryValidationError
)


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    storage_path = Path(temp_dir) / "storage"
    storage_path.mkdir(parents=True)
    
    # Create story pack directory
    story_pack_path = Path(temp_dir) / "storypacks"
    story_pack_path.mkdir(parents=True)
    
    yield {"storage": str(storage_path), "storypacks": str(story_pack_path)}
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_story_data():
    """Sample complete story data for testing."""
    return {
        "id": "test_adventure",
        "meta": {
            "title": "Test Adventure",
            "description": "A test story for validation",
            "author": "Test Author",
            "version": "1.0.0",
            "created": "2024-01-01T00:00:00Z",
            "modified": "2024-01-01T12:00:00Z",
            "tags": ["fantasy", "adventure"]
        },
        "characters": {
            "Alice": {
                "name": "Alice",
                "personality": "brave and curious",
                "background": "A young adventurer seeking her destiny",
                "stats": {
                    "strength": 8,
                    "intelligence": 9,
                    "charisma": 7,
                    "dexterity": 8
                },
                "appearance": "Tall with brown hair and green eyes",
                "motivation": "To discover the truth about her family's past"
            }
        },
        "world": {
            "setting": "A fantasy medieval world with magic",
            "time_period": "Medieval fantasy",
            "locations": {
                "village": {
                    "name": "Peaceful Village",
                    "description": "A quiet farming community",
                    "connections": ["forest", "mountains"]
                },
                "forest": {
                    "name": "Enchanted Forest", 
                    "description": "A magical woodland filled with mysteries",
                    "connections": ["village", "ruins"]
                }
            },
            "lore": {
                "magic_system": "Elemental magic based on nature",
                "history": "Ancient civilization ruins dot the landscape"
            }
        },
        "config": {
            "max_scenes": 50,
            "difficulty": "medium",
            "tone": "adventurous",
            "auto_save": True,
            "character_consistency": True
        },
        "templates": {
            "scene_templates": ["exploration", "dialogue", "action"],
            "character_templates": ["hero", "mentor", "villain"]
        }
    }


@pytest.fixture
def story_pack_data():
    """Sample story pack data for testing."""
    return {
        "pack_info": {
            "name": "Fantasy Pack",
            "version": "1.0",
            "description": "A collection of fantasy stories"
        },
        "stories": {
            "quest_story": {
                "title": "The Great Quest",
                "description": "An epic fantasy adventure"
            }
        }
    }


class TestStoryLoading:
    """Test basic story loading functionality."""
    
    def test_load_story_success(self, temp_storage_dir, sample_story_data):
        """Test successful story loading."""
        storage_path = temp_storage_dir["storage"]
        story_id = "test_adventure"
        
        # Create story directory and files
        story_dir = Path(storage_path) / story_id
        story_dir.mkdir(parents=True)
        
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        loaded_story = load_story(storage_path, story_id)
        
        assert loaded_story is not None
        assert loaded_story["id"] == story_id
        assert loaded_story["meta"]["title"] == "Test Adventure"
        assert "Alice" in loaded_story["characters"]
    
    def test_load_story_not_found(self, temp_storage_dir):
        """Test loading non-existent story."""
        storage_path = temp_storage_dir["storage"]
        
        loaded_story = load_story(storage_path, "nonexistent_story")
        
        assert loaded_story is None
    
    def test_load_story_corrupted_data(self, temp_storage_dir):
        """Test loading story with corrupted data."""
        storage_path = temp_storage_dir["storage"]
        story_id = "corrupted_story"
        
        story_dir = Path(storage_path) / story_id
        story_dir.mkdir(parents=True)
        
        # Create corrupted JSON file
        with open(story_dir / "story_data.json", 'w') as f:
            f.write("{ invalid json data")
        
        loaded_story = load_story(storage_path, story_id)
        
        assert loaded_story is None
    
    def test_load_story_with_canon(self, temp_storage_dir, sample_story_data):
        """Test loading story with canon files."""
        storage_path = temp_storage_dir["storage"]
        story_id = "test_adventure"
        
        # Create story directory
        story_dir = Path(storage_path) / story_id
        story_dir.mkdir(parents=True)
        
        # Create canon directory and files
        canon_dir = story_dir / "canon"
        canon_dir.mkdir()
        
        canon_files = {
            "world_lore.json": {"magic": "elemental", "gods": ["Solara", "Luneth"]},
            "character_guide.txt": "Characters should be consistent with their backgrounds",
            "location_details.md": "# Locations\n\nDetailed location descriptions"
        }
        
        for filename, content in canon_files.items():
            if filename.endswith('.json'):
                with open(canon_dir / filename, 'w') as f:
                    json.dump(content, f)
            else:
                with open(canon_dir / filename, 'w') as f:
                    f.write(content)
        
        # Save story data
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        loaded_story = load_story(storage_path, story_id, include_canon=True)
        
        assert loaded_story is not None
        assert "canon" in loaded_story
        assert len(loaded_story["canon"]) > 0
    
    def test_load_story_data_function(self, temp_storage_dir, sample_story_data):
        """Test load_story_data function specifically."""
        storage_path = temp_storage_dir["storage"]
        story_id = "test_story_data"
        
        story_dir = Path(storage_path) / story_id
        story_dir.mkdir(parents=True)
        
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        story_data = load_story_data(storage_path, story_id)
        
        assert story_data == sample_story_data


class TestStoryValidation:
    """Test story validation functionality."""
    
    def test_validate_story_structure_valid(self, sample_story_data):
        """Test validation with valid story structure."""
        result = validate_story_structure(sample_story_data)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0
    
    def test_validate_story_structure_missing_required(self):
        """Test validation with missing required fields."""
        invalid_story = {
            "id": "test_story",
            # Missing meta section
            "characters": {},
            "world": {}
        }
        
        result = validate_story_structure(invalid_story)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("meta" in error.lower() for error in result["errors"])
    
    def test_validate_story_structure_invalid_character(self):
        """Test validation with invalid character data."""
        invalid_story = {
            "id": "test_story",
            "meta": {"title": "Test"},
            "characters": {
                "Invalid": {
                    # Missing required name field
                    "personality": "test"
                }
            },
            "world": {}
        }
        
        result = validate_story_structure(invalid_story)
        
        assert result["valid"] is False
        assert any("character" in error.lower() for error in result["errors"])
    
    def test_validate_story_structure_warnings(self):
        """Test validation generates appropriate warnings."""
        story_with_warnings = {
            "id": "test_story",
            "meta": {"title": "Test Story"},
            "characters": {},  # Empty characters - should warn
            "world": {
                "setting": "Basic setting"
                # Missing locations - should warn
            }
        }
        
        result = validate_story_structure(story_with_warnings)
        
        assert result["valid"] is True  # Valid but with warnings
        assert len(result["warnings"]) > 0
    
    def test_validate_story_structure_empty(self):
        """Test validation with empty story data."""
        result = validate_story_structure({})
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestStoryInitialization:
    """Test story initialization functionality."""
    
    def test_initialize_story_basic(self, temp_storage_dir):
        """Test basic story initialization."""
        storage_path = temp_storage_dir["storage"]
        story_config = {
            "id": "new_story",
            "title": "New Adventure",
            "description": "A brand new story",
            "author": "Story Creator"
        }
        
        result = initialize_story(storage_path, story_config)
        
        assert result is True
        
        # Check story was created
        story_dir = Path(storage_path) / "new_story"
        assert story_dir.exists()
        assert (story_dir / "story_data.json").exists()
        
        # Check story structure
        with open(story_dir / "story_data.json", 'r') as f:
            story_data = json.load(f)
        
        assert story_data["id"] == "new_story"
        assert story_data["meta"]["title"] == "New Adventure"
        assert "characters" in story_data
        assert "world" in story_data
    
    def test_initialize_story_with_template(self, temp_storage_dir):
        """Test story initialization with template."""
        storage_path = temp_storage_dir["storage"]
        template_config = {
            "template": "fantasy_adventure",
            "characters": ["hero", "mentor"],
            "world_type": "medieval_fantasy"
        }
        
        story_config = {
            "id": "template_story",
            "title": "Template Adventure",
            "template_config": template_config
        }
        
        result = initialize_story(storage_path, story_config)
        
        assert result is True
        
        # Verify template was applied
        story_data = load_story_data(storage_path, "template_story")
        assert "template_config" in story_data
    
    def test_initialize_story_existing_id(self, temp_storage_dir, sample_story_data):
        """Test initializing story with existing ID."""
        storage_path = temp_storage_dir["storage"]
        
        # Create existing story
        story_dir = Path(storage_path) / "existing_story"
        story_dir.mkdir(parents=True)
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        # Try to initialize with same ID
        story_config = {
            "id": "existing_story",
            "title": "Duplicate Story"
        }
        
        result = initialize_story(storage_path, story_config, overwrite=False)
        
        assert result is False
    
    def test_initialize_story_with_overwrite(self, temp_storage_dir, sample_story_data):
        """Test initializing story with overwrite enabled."""
        storage_path = temp_storage_dir["storage"]
        
        # Create existing story
        story_dir = Path(storage_path) / "overwrite_story"
        story_dir.mkdir(parents=True)
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        # Initialize with overwrite
        story_config = {
            "id": "overwrite_story",
            "title": "New Title"
        }
        
        result = initialize_story(storage_path, story_config, overwrite=True)
        
        assert result is True
        
        # Verify story was overwritten
        new_story_data = load_story_data(storage_path, "overwrite_story")
        assert new_story_data["meta"]["title"] == "New Title"


class TestStoryDiscovery:
    """Test story discovery and listing functionality."""
    
    def test_get_available_stories(self, temp_storage_dir, sample_story_data):
        """Test getting list of available stories."""
        storage_path = temp_storage_dir["storage"]
        
        # Create multiple stories
        stories = ["story1", "story2", "story3"]
        for story_id in stories:
            story_dir = Path(storage_path) / story_id
            story_dir.mkdir(parents=True)
            
            story_data = sample_story_data.copy()
            story_data["id"] = story_id
            story_data["meta"]["title"] = f"Story {story_id}"
            
            with open(story_dir / "story_data.json", 'w') as f:
                json.dump(story_data, f)
        
        available_stories = get_available_stories(storage_path)
        
        assert isinstance(available_stories, list)
        assert len(available_stories) == 3
        assert all(story in stories for story in available_stories)
    
    def test_get_available_stories_with_metadata(self, temp_storage_dir, sample_story_data):
        """Test getting stories with metadata."""
        storage_path = temp_storage_dir["storage"]
        
        story_dir = Path(storage_path) / "metadata_story"
        story_dir.mkdir(parents=True)
        
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        available_stories = get_available_stories(storage_path, include_metadata=True)
        
        assert isinstance(available_stories, list)
        assert len(available_stories) == 1
        assert isinstance(available_stories[0], dict)
        assert "id" in available_stories[0]
        assert "meta" in available_stories[0]
    
    def test_get_available_stories_empty_directory(self, temp_storage_dir):
        """Test getting stories from empty directory."""
        storage_path = temp_storage_dir["storage"]
        
        available_stories = get_available_stories(storage_path)
        
        assert available_stories == []


class TestTemplateSystem:
    """Test story template system."""
    
    def test_create_story_from_template_basic(self, temp_storage_dir):
        """Test creating story from basic template."""
        storage_path = temp_storage_dir["storage"]
        
        template_data = {
            "meta": {
                "template_name": "basic_adventure",
                "template_version": "1.0"
            },
            "characters": {
                "hero": {
                    "name": "{{hero_name}}",
                    "personality": "brave and determined"
                }
            },
            "world": {
                "setting": "{{world_setting}}"
            }
        }
        
        variables = {
            "hero_name": "Alex",
            "world_setting": "post-apocalyptic wasteland"
        }
        
        story_config = {
            "id": "template_story",
            "title": "Template Story"
        }
        
        result = create_story_from_template(storage_path, template_data, story_config, variables)
        
        assert result is True
        
        # Verify template variables were replaced
        story_data = load_story_data(storage_path, "template_story")
        assert story_data["characters"]["hero"]["name"] == "Alex"
        assert story_data["world"]["setting"] == "post-apocalyptic wasteland"
    
    def test_create_story_from_template_complex(self, temp_storage_dir):
        """Test creating story from complex template."""
        storage_path = temp_storage_dir["storage"]
        
        template_data = {
            "meta": {"template_name": "complex_template"},
            "characters": {
                "protagonist": {
                    "name": "{{protag_name}}",
                    "stats": {
                        "strength": "{{protag_strength}}",
                        "intelligence": "{{protag_intelligence}}"
                    }
                }
            },
            "world": {
                "locations": {
                    "starting_location": {
                        "name": "{{start_location_name}}",
                        "description": "{{start_location_desc}}"
                    }
                }
            }
        }
        
        variables = {
            "protag_name": "Maya",
            "protag_strength": 7,
            "protag_intelligence": 9,
            "start_location_name": "Cyber City",
            "start_location_desc": "A neon-lit metropolis of the future"
        }
        
        story_config = {
            "id": "complex_template_story",
            "title": "Complex Template Story"
        }
        
        result = create_story_from_template(storage_path, template_data, story_config, variables)
        
        assert result is True
        
        story_data = load_story_data(storage_path, "complex_template_story")
        assert story_data["characters"]["protagonist"]["name"] == "Maya"
        assert story_data["characters"]["protagonist"]["stats"]["strength"] == 7
        assert story_data["world"]["locations"]["starting_location"]["name"] == "Cyber City"


class TestStoryLoader:
    """Test StoryLoader class functionality."""
    
    def test_story_loader_init(self, temp_storage_dir):
        """Test StoryLoader initialization."""
        loader = StoryLoader(temp_storage_dir["storage"])
        
        assert loader.storage_path == temp_storage_dir["storage"]
        assert hasattr(loader, 'cache')
    
    def test_story_loader_load_with_cache(self, temp_storage_dir, sample_story_data):
        """Test StoryLoader with caching."""
        storage_path = temp_storage_dir["storage"]
        loader = StoryLoader(storage_path)
        
        # Create story
        story_dir = Path(storage_path) / "cached_story"
        story_dir.mkdir(parents=True)
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        # Load story twice
        story1 = loader.load_story("cached_story")
        story2 = loader.load_story("cached_story")
        
        assert story1 is not None
        assert story2 is not None
        assert story1 == story2
        # Should be cached
        assert "cached_story" in loader.cache
    
    def test_story_loader_invalidate_cache(self, temp_storage_dir, sample_story_data):
        """Test cache invalidation."""
        storage_path = temp_storage_dir["storage"]
        loader = StoryLoader(storage_path)
        
        # Create and load story
        story_dir = Path(storage_path) / "cache_test_story"
        story_dir.mkdir(parents=True)
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        story = loader.load_story("cache_test_story")
        assert "cache_test_story" in loader.cache
        
        # Invalidate cache
        loader.invalidate_cache("cache_test_story")
        assert "cache_test_story" not in loader.cache
    
    def test_story_loader_preload_stories(self, temp_storage_dir, sample_story_data):
        """Test preloading multiple stories."""
        storage_path = temp_storage_dir["storage"]
        loader = StoryLoader(storage_path)
        
        # Create multiple stories
        story_ids = ["preload1", "preload2", "preload3"]
        for story_id in story_ids:
            story_dir = Path(storage_path) / story_id
            story_dir.mkdir(parents=True)
            
            story_data = sample_story_data.copy()
            story_data["id"] = story_id
            
            with open(story_dir / "story_data.json", 'w') as f:
                json.dump(story_data, f)
        
        # Preload stories
        loader.preload_stories(story_ids)
        
        # All should be in cache
        for story_id in story_ids:
            assert story_id in loader.cache
    
    def test_story_loader_get_story_info(self, temp_storage_dir, sample_story_data):
        """Test getting story info without full load."""
        storage_path = temp_storage_dir["storage"]
        loader = StoryLoader(storage_path)
        
        # Create story
        story_dir = Path(storage_path) / "info_test_story"
        story_dir.mkdir(parents=True)
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(sample_story_data, f)
        
        info = loader.get_story_info("info_test_story")
        
        assert isinstance(info, dict)
        assert "id" in info
        assert "meta" in info
        # Should only contain basic info, not full story
        assert "characters" not in info or len(info["characters"]) == 0


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_story_validation_error(self):
        """Test StoryValidationError exception."""
        errors = ["Missing meta section", "Invalid character data"]
        
        error = StoryValidationError("Validation failed", errors)
        
        assert str(error) == "Validation failed"
        assert error.validation_errors == errors
    
    def test_load_story_permission_error(self, temp_storage_dir):
        """Test handling permission errors during load."""
        storage_path = temp_storage_dir["storage"]
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            story = load_story(storage_path, "permission_test")
        
        assert story is None
    
    def test_initialize_story_io_error(self, temp_storage_dir):
        """Test handling IO errors during initialization."""
        storage_path = temp_storage_dir["storage"]
        
        story_config = {
            "id": "io_error_test",
            "title": "IO Error Test"
        }
        
        with patch('pathlib.Path.mkdir', side_effect=OSError("Disk full")):
            result = initialize_story(storage_path, story_config)
        
        assert result is False
    
    def test_validate_story_type_error(self):
        """Test validation with wrong data types."""
        invalid_story = "This should be a dictionary"
        
        result = validate_story_structure(invalid_story)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestPerformanceOptimization:
    """Test performance optimization features."""
    
    def test_lazy_loading(self, temp_storage_dir, sample_story_data):
        """Test lazy loading of story components."""
        storage_path = temp_storage_dir["storage"]
        loader = StoryLoader(storage_path, lazy_load=True)
        
        # Create story with large data
        large_story_data = sample_story_data.copy()
        large_story_data["large_data"] = "x" * 10000  # Large content
        
        story_dir = Path(storage_path) / "lazy_test_story"
        story_dir.mkdir(parents=True)
        with open(story_dir / "story_data.json", 'w') as f:
            json.dump(large_story_data, f)
        
        # Load with lazy loading
        story = loader.load_story("lazy_test_story", components=["meta", "characters"])
        
        assert story is not None
        assert "meta" in story
        assert "characters" in story
        # Large data should not be loaded
        assert "large_data" not in story
    
    def test_concurrent_loading(self, temp_storage_dir, sample_story_data):
        """Test concurrent story loading."""
        import threading
        import time
        
        storage_path = temp_storage_dir["storage"]
        loader = StoryLoader(storage_path)
        
        # Create multiple stories
        story_ids = [f"concurrent_{i}" for i in range(5)]
        for story_id in story_ids:
            story_dir = Path(storage_path) / story_id
            story_dir.mkdir(parents=True)
            
            story_data = sample_story_data.copy()
            story_data["id"] = story_id
            
            with open(story_dir / "story_data.json", 'w') as f:
                json.dump(story_data, f)
        
        results = []
        
        def load_story_worker(story_id):
            story = loader.load_story(story_id)
            results.append(story is not None)
            time.sleep(0.1)  # Simulate processing time
        
        # Create and start threads
        threads = []
        for story_id in story_ids:
            thread = threading.Thread(target=load_story_worker, args=[story_id])
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All loads should succeed
        assert all(results)
        assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__])

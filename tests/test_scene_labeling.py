"""
Test suite for Scene Labeling and Bookmarking System.
"""

import unittest
import os
import tempfile
import shutil
from datetime import datetime
import sys

# Add the parent directory to the path so we can import our modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.scene_logger import save_scene, load_scene, update_scene_label, get_scenes_by_label, get_labeled_scenes
from core.bookmark_manager import BookmarkManager
from core.timeline_builder import TimelineBuilder
from core.database import init_database

class TestSceneLabeling(unittest.TestCase):
    """Test scene labeling functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_labeling"
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize database
        init_database(self.test_story_id)
        
        # Create test scenes
        self.scene1_id = save_scene(
            self.test_story_id,
            "Hello, I'm starting a new adventure",
            "Welcome to the mystical realm of Eldoria!",
            scene_label="Chapter 1: The Beginning"
        )
        
        self.scene2_id = save_scene(
            self.test_story_id,
            "I look around the forest",
            "You see tall ancient trees and hear mysterious sounds",
            scene_label="Forest Exploration"
        )
        
        self.scene3_id = save_scene(
            self.test_story_id,
            "I continue on the path",
            "The path winds deeper into the forest",
            scene_label=None  # No label
        )
    
    def tearDown(self):
        """Clean up test environment."""
        # Close any open database connections
        import sqlite3
        import gc
        gc.collect()
        
        os.chdir(self.original_cwd)
        # Try to remove temp directory with retry
        try:
            shutil.rmtree(self.temp_dir)
        except PermissionError:
            # On Windows, sometimes files are still locked
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                pass  # Ignore if still locked
    
    def test_save_scene_with_label(self):
        """Test saving scene with label."""
        scene_id = save_scene(
            self.test_story_id,
            "Test input",
            "Test output",
            scene_label="Test Label"
        )
        
        scene = load_scene(self.test_story_id, scene_id)
        self.assertEqual(scene['scene_label'], "Test Label")
    
    def test_save_scene_without_label(self):
        """Test saving scene without label."""
        scene_id = save_scene(
            self.test_story_id,
            "Test input",
            "Test output"
        )
        
        scene = load_scene(self.test_story_id, scene_id)
        self.assertIsNone(scene['scene_label'])
    
    def test_update_scene_label(self):
        """Test updating scene label."""
        # Update label
        success = update_scene_label(self.test_story_id, self.scene3_id, "Updated Label")
        self.assertTrue(success)
        
        # Verify update
        scene = load_scene(self.test_story_id, self.scene3_id)
        self.assertEqual(scene['scene_label'], "Updated Label")
    
    def test_get_scenes_by_label(self):
        """Test getting scenes by label."""
        scenes = get_scenes_by_label(self.test_story_id, "Forest Exploration")
        self.assertEqual(len(scenes), 1)
        self.assertEqual(scenes[0]['scene_id'], self.scene2_id)
    
    def test_get_labeled_scenes(self):
        """Test getting all labeled scenes."""
        labeled_scenes = get_labeled_scenes(self.test_story_id)
        self.assertEqual(len(labeled_scenes), 2)  # scene1 and scene2 have labels
        
        labels = [scene['scene_label'] for scene in labeled_scenes]
        self.assertIn("Chapter 1: The Beginning", labels)
        self.assertIn("Forest Exploration", labels)


class TestBookmarkManager(unittest.TestCase):
    """Test bookmark management functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_bookmarks"
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize database and create test scenes
        init_database(self.test_story_id)
        
        self.scene1_id = save_scene(
            self.test_story_id,
            "Test scene 1",
            "Test output 1"
        )
        
        self.scene2_id = save_scene(
            self.test_story_id,
            "Test scene 2",
            "Test output 2"
        )
        
        self.bookmark_manager = BookmarkManager(self.test_story_id)
    
    def tearDown(self):
        """Clean up test environment."""
        # Close any open database connections
        import sqlite3
        import gc
        gc.collect()
        
        os.chdir(self.original_cwd)
        # Try to remove temp directory with retry
        try:
            shutil.rmtree(self.temp_dir)
        except PermissionError:
            # On Windows, sometimes files are still locked
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                pass  # Ignore if still locked
    
    def test_create_bookmark(self):
        """Test creating a bookmark."""
        bookmark_id = self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="Important Scene",
            description="This is an important scene",
            bookmark_type="user"
        )
        
        self.assertIsInstance(bookmark_id, int)
        self.assertGreater(bookmark_id, 0)
    
    def test_get_bookmark(self):
        """Test getting a bookmark."""
        bookmark_id = self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="Test Bookmark",
            description="Test description"
        )
        
        bookmark = self.bookmark_manager.get_bookmark(bookmark_id)
        self.assertIsNotNone(bookmark)
        self.assertEqual(bookmark['label'], "Test Bookmark")
        self.assertEqual(bookmark['scene_id'], self.scene1_id)
    
    def test_create_duplicate_bookmark(self):
        """Test creating duplicate bookmark fails."""
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="Duplicate",
            description="First bookmark"
        )
        
        with self.assertRaises(ValueError):
            self.bookmark_manager.create_bookmark(
                scene_id=self.scene1_id,
                label="Duplicate",
                description="Second bookmark"
            )
    
    def test_list_bookmarks(self):
        """Test listing bookmarks."""
        # Create test bookmarks
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="User Bookmark",
            bookmark_type="user"
        )
        
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene2_id,
            label="Chapter Bookmark",
            bookmark_type="chapter"
        )
        
        # Test listing all bookmarks
        all_bookmarks = self.bookmark_manager.list_bookmarks()
        self.assertEqual(len(all_bookmarks), 2)
        
        # Test filtering by type
        user_bookmarks = self.bookmark_manager.list_bookmarks(bookmark_type="user")
        self.assertEqual(len(user_bookmarks), 1)
        self.assertEqual(user_bookmarks[0]['label'], "User Bookmark")
    
    def test_update_bookmark(self):
        """Test updating a bookmark."""
        bookmark_id = self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="Original Label",
            description="Original description"
        )
        
        # Update bookmark
        success = self.bookmark_manager.update_bookmark(
            bookmark_id=bookmark_id,
            label="Updated Label",
            description="Updated description"
        )
        
        self.assertTrue(success)
        
        # Verify update
        bookmark = self.bookmark_manager.get_bookmark(bookmark_id)
        self.assertEqual(bookmark['label'], "Updated Label")
        self.assertEqual(bookmark['description'], "Updated description")
    
    def test_delete_bookmark(self):
        """Test deleting a bookmark."""
        bookmark_id = self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="To Delete",
            description="This will be deleted"
        )
        
        # Delete bookmark
        success = self.bookmark_manager.delete_bookmark(bookmark_id)
        self.assertTrue(success)
        
        # Verify deletion
        bookmark = self.bookmark_manager.get_bookmark(bookmark_id)
        self.assertIsNone(bookmark)
    
    def test_search_bookmarks(self):
        """Test searching bookmarks."""
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="Important Scene",
            description="This is very important"
        )
        
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene2_id,
            label="Battle Scene",
            description="Epic battle sequence"
        )
        
        # Search by label
        results = self.bookmark_manager.search_bookmarks("Important")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['label'], "Important Scene")
        
        # Search by description
        results = self.bookmark_manager.search_bookmarks("battle")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['label'], "Battle Scene")
    
    def test_auto_create_chapter_bookmark(self):
        """Test auto-creating chapter bookmark."""
        bookmark_id = self.bookmark_manager.auto_create_chapter_bookmark(
            scene_id=self.scene1_id,
            chapter_title="Chapter 1",
            chapter_level=1
        )
        
        bookmark = self.bookmark_manager.get_bookmark(bookmark_id)
        self.assertEqual(bookmark['label'], "Chapter 1")
        self.assertEqual(bookmark['bookmark_type'], "chapter")
        self.assertEqual(bookmark['metadata']['chapter_level'], 1)
        self.assertTrue(bookmark['metadata']['auto_generated'])
    
    def test_bookmark_stats(self):
        """Test bookmark statistics."""
        # Create bookmarks of different types
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="User 1",
            bookmark_type="user"
        )
        
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene2_id,
            label="User 2",
            bookmark_type="user"
        )
        
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="Chapter 1",
            bookmark_type="chapter"
        )
        
        stats = self.bookmark_manager.get_stats()
        self.assertEqual(stats['total_bookmarks'], 3)
        self.assertEqual(stats['by_type']['user'], 2)
        self.assertEqual(stats['by_type']['chapter'], 1)


class TestTimelineBuilder(unittest.TestCase):
    """Test timeline building functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_timeline"
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize database
        init_database(self.test_story_id)
        
        # Create test scenes
        self.scene1_id = save_scene(
            self.test_story_id,
            "Chapter 1 starts",
            "Beginning of the story",
            scene_label="Chapter 1"
        )
        
        self.scene2_id = save_scene(
            self.test_story_id,
            "Action sequence",
            "Exciting action happens",
            scene_label="Action Scene"
        )
        
        self.scene3_id = save_scene(
            self.test_story_id,
            "Chapter 2 begins",
            "New chapter starts",
            scene_label="Chapter 2"
        )
        
        # Create bookmarks
        self.bookmark_manager = BookmarkManager(self.test_story_id)
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene1_id,
            label="Chapter 1",
            bookmark_type="chapter"
        )
        
        self.bookmark_manager.create_bookmark(
            scene_id=self.scene3_id,
            label="Chapter 2",
            bookmark_type="chapter"
        )
        
        self.timeline_builder = TimelineBuilder(self.test_story_id)
    
    def tearDown(self):
        """Clean up test environment."""
        # Close any open database connections
        import sqlite3
        import gc
        gc.collect()
        
        os.chdir(self.original_cwd)
        # Try to remove temp directory with retry
        try:
            shutil.rmtree(self.temp_dir)
        except PermissionError:
            # On Windows, sometimes files are still locked
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                pass  # Ignore if still locked
    
    def test_get_full_timeline(self):
        """Test getting full timeline."""
        timeline = self.timeline_builder.get_full_timeline()
        
        self.assertEqual(timeline['story_id'], self.test_story_id)
        self.assertEqual(timeline['total_scenes'], 3)
        self.assertEqual(timeline['total_bookmarks'], 2)
        self.assertEqual(len(timeline['timeline']), 3)
        
        # Check that bookmarks are associated with scenes
        scene1_entry = timeline['timeline'][0]
        self.assertEqual(len(scene1_entry['bookmarks']), 1)
        self.assertEqual(scene1_entry['bookmarks'][0]['label'], "Chapter 1")
    
    def test_get_chapter_timeline(self):
        """Test getting chapter timeline."""
        timeline = self.timeline_builder.get_chapter_timeline()
        
        self.assertEqual(timeline['story_id'], self.test_story_id)
        self.assertEqual(timeline['total_chapters'], 2)
        
        # Check chapter structure
        chapters = timeline['chapters']
        self.assertEqual(len(chapters), 2)
        
        # First chapter should have scenes 1 and 2
        first_chapter = chapters[0]
        self.assertEqual(first_chapter['chapter']['label'], "Chapter 1")
        self.assertEqual(first_chapter['scene_count'], 2)
    
    def test_get_labeled_timeline(self):
        """Test getting labeled timeline."""
        timeline = self.timeline_builder.get_labeled_timeline()
        
        self.assertEqual(timeline['story_id'], self.test_story_id)
        self.assertEqual(timeline['total_labels'], 3)
        self.assertEqual(timeline['total_labeled_scenes'], 3)
        
        # Check labeled scenes grouping
        labeled_scenes = timeline['labeled_scenes']
        self.assertIn("Chapter 1", labeled_scenes)
        self.assertIn("Action Scene", labeled_scenes)
        self.assertIn("Chapter 2", labeled_scenes)
    
    def test_get_navigation_menu(self):
        """Test getting navigation menu."""
        menu = self.timeline_builder.get_navigation_menu()
        
        self.assertEqual(menu['story_id'], self.test_story_id)
        self.assertEqual(len(menu['chapters']), 2)
        self.assertEqual(len(menu['labeled_scenes']), 3)
        self.assertEqual(len(menu['recent_scenes']), 3)
    
    def test_export_timeline_json(self):
        """Test exporting timeline as JSON."""
        json_timeline = self.timeline_builder.export_timeline_json()
        self.assertIsInstance(json_timeline, str)
        self.assertIn(self.test_story_id, json_timeline)
        
        # Test minimal export
        minimal_json = self.timeline_builder.export_timeline_json(include_content=False)
        self.assertIsInstance(minimal_json, str)
    
    def test_export_timeline_markdown(self):
        """Test exporting timeline as Markdown."""
        markdown = self.timeline_builder.export_timeline_markdown()
        self.assertIsInstance(markdown, str)
        self.assertIn(f"# Story Timeline: {self.test_story_id}", markdown)
        self.assertIn("## Chapter 1", markdown)
        self.assertIn("## Action Scene", markdown)
    
    def test_get_scene_context(self):
        """Test getting scene context."""
        context = self.timeline_builder.get_scene_context(self.scene2_id, context_window=1)
        
        self.assertEqual(context['target_scene_id'], self.scene2_id)
        self.assertEqual(context['context_window'], 1)
        self.assertEqual(len(context['scenes']), 3)  # scene1, scene2, scene3
        
        # Check that target scene is marked
        target_scene = next(s for s in context['scenes'] if s['is_target'])
        self.assertEqual(target_scene['scene_id'], self.scene2_id)
    
    def test_get_stats(self):
        """Test getting timeline statistics."""
        stats = self.timeline_builder.get_stats()
        
        self.assertEqual(stats['story_id'], self.test_story_id)
        self.assertEqual(stats['scenes']['total'], 3)
        self.assertEqual(stats['scenes']['labeled'], 3)
        self.assertEqual(stats['scenes']['unlabeled'], 0)
        self.assertEqual(stats['bookmarks']['total_bookmarks'], 2)
        self.assertTrue(stats['timeline_coverage']['has_chapters'])
        self.assertEqual(stats['timeline_coverage']['labeling_percentage'], 100.0)


if __name__ == '__main__':
    unittest.main()

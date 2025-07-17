"""
Test suite for OpenChronicle Full-Text Search (FTS5) System.

This test suite covers:
- FTS5 database schema and indexing
- Search engine functionality
- Query parsing and sanitization
- Search result ranking and snippets
- Integration with existing systems
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

from core.database import init_database, check_fts_support, optimize_fts_index, get_fts_stats, execute_insert
from core.search_engine import SearchEngine, SearchResult, SearchQuery, search_story
from core.scene_logger import save_scene
from core.memory_manager import update_character_memory, update_world_state


def store_memory_for_testing(story_id, memory_type, key, value):
    """Helper function to store memory for testing purposes."""
    execute_insert(story_id, '''
        INSERT INTO memory (story_id, type, key, value, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (story_id, memory_type, key, f'"{value}"', 
          datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))


class TestFTSSupport(unittest.TestCase):
    """Test FTS5 support detection."""
    
    def test_fts_support_detection(self):
        """Test that FTS5 support is properly detected."""
        fts_supported = check_fts_support()
        self.assertIsInstance(fts_supported, bool)
        
        # If FTS5 is supported, we should be able to create a SearchEngine
        if fts_supported:
            # This should not raise an exception
            temp_dir = tempfile.mkdtemp()
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                init_database("test_story")
                engine = SearchEngine("test_story")
                self.assertIsNotNone(engine)
            finally:
                os.chdir(original_cwd)
                shutil.rmtree(temp_dir)


class TestFTSDatabase(unittest.TestCase):
    """Test FTS5 database schema and operations."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_fts"
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize database
        init_database(self.test_story_id)
        
        # Check if FTS5 is supported
        if not check_fts_support():
            self.skipTest("FTS5 is not supported in this SQLite version")
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_fts_tables_creation(self):
        """Test that FTS5 virtual tables are created."""
        stats = get_fts_stats(self.test_story_id)
        
        # Check that FTS tables exist
        self.assertIn('scenes_fts', stats['fts_tables'])
        self.assertIn('memory_fts', stats['fts_tables'])
        
        # Check initial counts
        self.assertEqual(stats['scenes_fts_entries'], 0)
        self.assertEqual(stats['memory_fts_entries'], 0)
    
    def test_fts_indexing_scenes(self):
        """Test that scenes are automatically indexed."""
        # Create a test scene
        scene_id = save_scene(
            self.test_story_id,
            "The hero enters the dark forest",
            "You find yourself in a mysterious woodland filled with ancient trees",
            scene_label="Forest Entry"
        )
        
        # Check that it was indexed
        stats = get_fts_stats(self.test_story_id)
        self.assertEqual(stats['scenes_fts_entries'], 1)
    
    def test_fts_indexing_memory(self):
        """Test that memory is automatically indexed."""
        # Create memory entries
        store_memory_for_testing(self.test_story_id, 'character', 'hero_name', 'Aragorn the Brave')
        store_memory_for_testing(self.test_story_id, 'world', 'location', 'Enchanted Forest')
        
        # Check that they were indexed
        stats = get_fts_stats(self.test_story_id)
        self.assertEqual(stats['memory_fts_entries'], 2)
    
    def test_fts_optimization(self):
        """Test FTS5 index optimization."""
        # Create some test data
        save_scene(self.test_story_id, "test input", "test output")
        
        # Optimize indexes (should not raise an exception)
        optimize_fts_index(self.test_story_id)
        
        # Verify data is still there
        stats = get_fts_stats(self.test_story_id)
        self.assertEqual(stats['scenes_fts_entries'], 1)


class TestSearchEngine(unittest.TestCase):
    """Test SearchEngine functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_search"
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize database
        init_database(self.test_story_id)
        
        # Check if FTS5 is supported
        if not check_fts_support():
            self.skipTest("FTS5 is not supported in this SQLite version")
        
        # Create SearchEngine
        self.engine = SearchEngine(self.test_story_id)
        
        # Create test data
        self.scene1_id = save_scene(
            self.test_story_id,
            "I want to explore the ancient castle",
            "You approach the massive stone fortress with its towering walls",
            scene_label="Castle Approach"
        )
        
        self.scene2_id = save_scene(
            self.test_story_id,
            "I examine the mysterious door",
            "The door is covered in strange runes and symbols",
            scene_label="Mysterious Door"
        )
        
        self.scene3_id = save_scene(
            self.test_story_id,
            "I cast a fire spell",
            "Flames dance from your fingertips, illuminating the dark corridor",
            scene_label="Fire Magic"
        )
        
        # Create memory data
        store_memory_for_testing(self.test_story_id, 'character', 'hero_name', 'Gandalf the Grey')
        store_memory_for_testing(self.test_story_id, 'character', 'hero_class', 'Wizard')
        store_memory_for_testing(self.test_story_id, 'world', 'current_location', 'Ancient Castle')
        store_memory_for_testing(self.test_story_id, 'world', 'discovered_items', 'Magic Staff, Ancient Key')
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_search_engine_initialization(self):
        """Test SearchEngine initialization."""
        self.assertEqual(self.engine.story_id, self.test_story_id)
        self.assertTrue(self.engine.fts_supported)
    
    def test_query_parsing_simple(self):
        """Test parsing of simple queries."""
        query = self.engine.parse_query("castle ancient")
        
        self.assertEqual(query.original, "castle ancient")
        self.assertEqual(query.sanitized, "castle ancient")
        self.assertEqual(query.terms, ["castle", "ancient"])
        self.assertEqual(query.operators, [])
        self.assertEqual(query.quoted_phrases, [])
        self.assertEqual(query.filters, {})
        self.assertEqual(query.content_types, ['scene', 'memory'])
    
    def test_query_parsing_quoted_phrases(self):
        """Test parsing of quoted phrases."""
        query = self.engine.parse_query('castle "ancient fortress" door')
        
        self.assertIn("ancient fortress", query.quoted_phrases)
        self.assertIn("castle", query.terms)
        self.assertIn("door", query.terms)
    
    def test_query_parsing_operators(self):
        """Test parsing of boolean operators."""
        query = self.engine.parse_query("castle AND door OR magic")
        
        self.assertIn("AND", query.operators)
        self.assertIn("OR", query.operators)
        self.assertIn("castle", query.terms)
        self.assertIn("door", query.terms)
        self.assertIn("magic", query.terms)
    
    def test_query_parsing_filters(self):
        """Test parsing of filters."""
        query = self.engine.parse_query("castle type:scene label:approach")
        
        self.assertEqual(query.filters['type'], 'scene')
        self.assertEqual(query.filters['label'], 'approach')
        self.assertEqual(query.content_types, ['scene'])
    
    def test_search_scenes_simple(self):
        """Test simple scene search."""
        query = self.engine.parse_query("castle")
        results = self.engine.search_scenes(query)
        
        # Should find the castle scene
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content_type, 'scene')
        self.assertEqual(results[0].id, self.scene1_id)
        self.assertIn("castle", results[0].content.lower())
    
    def test_search_scenes_with_label_filter(self):
        """Test scene search with label filter."""
        query = self.engine.parse_query("door label:mysterious")
        results = self.engine.search_scenes(query)
        
        # Should find the mysterious door scene
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.scene2_id)
        self.assertEqual(results[0].scene_label, "Mysterious Door")
    
    def test_search_memory_simple(self):
        """Test simple memory search."""
        query = self.engine.parse_query("Gandalf")
        results = self.engine.search_memory(query)
        
        # Should find the character memory
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content_type, 'memory')
        self.assertIn("Gandalf", results[0].content)
    
    def test_search_memory_with_type_filter(self):
        """Test memory search with type filter."""
        query = self.engine.parse_query("castle memtype:world")
        results = self.engine.search_memory(query)
        
        # Should find the world memory about castle
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata['memory_type'], 'world')
        self.assertIn("Castle", results[0].content)
    
    def test_search_all_content_types(self):
        """Test searching across all content types."""
        results = self.engine.search_all("castle")
        
        # Should find both scene and memory results
        self.assertGreater(len(results), 0)
        
        # Check that we have different content types
        content_types = {result.content_type for result in results}
        self.assertIn('scene', content_types)
        self.assertIn('memory', content_types)
    
    def test_search_with_quoted_phrases(self):
        """Test search with quoted phrases."""
        query = self.engine.parse_query('"Ancient Castle"')
        results = self.engine.search_memory(query)
        
        # Should find the exact phrase match
        self.assertEqual(len(results), 1)
        self.assertIn("Ancient Castle", results[0].content)
    
    def test_search_ranking(self):
        """Test that search results are ranked by relevance."""
        # Create a scene with multiple matches
        save_scene(
            self.test_story_id,
            "The castle door is ancient and mysterious",
            "This ancient castle door holds many secrets",
            scene_label="Castle Door Investigation"
        )
        
        results = self.engine.search_all("castle door ancient")
        
        # Should have results
        self.assertGreater(len(results), 0)
        
        # Check that scores are in descending order (lower is better for BM25)
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i].score, results[i + 1].score)
    
    def test_search_snippets(self):
        """Test that search results include snippets."""
        results = self.engine.search_all("castle")
        
        # Should have results with snippets
        self.assertGreater(len(results), 0)
        
        for result in results:
            self.assertIsInstance(result.snippet, str)
            self.assertGreater(len(result.snippet), 0)
    
    def test_search_no_results(self):
        """Test search with no matching results."""
        results = self.engine.search_all("nonexistent_term_xyz")
        
        # Should return empty list
        self.assertEqual(len(results), 0)
    
    def test_search_stats(self):
        """Test search engine statistics."""
        stats = self.engine.get_search_stats()
        
        self.assertTrue(stats['fts_supported'])
        self.assertEqual(stats['story_id'], self.test_story_id)
        self.assertGreater(stats['indexed_scenes'], 0)
        self.assertGreater(stats['indexed_memory'], 0)
    
    def test_health_check(self):
        """Test search engine health check."""
        health = self.engine.health_check()
        
        self.assertEqual(health['status'], 'healthy')
        self.assertTrue(health['fts_supported'])
        self.assertTrue(health['search_functional'])
        self.assertTrue(health['fts_integrity'])
        self.assertEqual(len(health['issues']), 0)
    
    def test_index_optimization(self):
        """Test FTS5 index optimization."""
        # Should not raise an exception
        self.engine.optimize_indexes()
        
        # Verify search still works
        results = self.engine.search_all("castle")
        self.assertGreater(len(results), 0)


class TestSearchConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for search."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_convenience"
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize database
        init_database(self.test_story_id)
        
        # Check if FTS5 is supported
        if not check_fts_support():
            self.skipTest("FTS5 is not supported in this SQLite version")
        
        # Create test data
        save_scene(
            self.test_story_id,
            "I explore the enchanted forest",
            "You discover a magical clearing with glowing flowers",
            scene_label="Forest Discovery"
        )
        
        store_memory_for_testing(self.test_story_id, 'world', 'forest_type', 'Enchanted Forest')
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_search_story_function(self):
        """Test search_story convenience function."""
        results = search_story(self.test_story_id, "forest")
        
        # Should find both scene and memory results
        self.assertGreater(len(results), 0)
        
        # Check that we have different content types
        content_types = {result.content_type for result in results}
        self.assertTrue(len(content_types) >= 1)


class TestSearchIntegration(unittest.TestCase):
    """Test integration with existing systems."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_integration"
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize database
        init_database(self.test_story_id)
        
        # Check if FTS5 is supported
        if not check_fts_support():
            self.skipTest("FTS5 is not supported in this SQLite version")
        
        # Create SearchEngine
        self.engine = SearchEngine(self.test_story_id)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_search_with_scene_labels(self):
        """Test search integration with scene labeling system."""
        # Create scenes with labels
        save_scene(
            self.test_story_id,
            "I begin my quest",
            "Your epic journey starts here",
            scene_label="Chapter 1: The Beginning"
        )
        
        save_scene(
            self.test_story_id,
            "I face the dragon",
            "A mighty dragon blocks your path",
            scene_label="Chapter 5: Dragon Fight"
        )
        
        # Search with label filter
        results = self.engine.search_all("quest label:beginning")
        
        # Should find the first scene
        self.assertEqual(len(results), 1)
        self.assertIn("Chapter 1", results[0].scene_label)
    
    def test_search_with_memory_types(self):
        """Test search integration with memory management."""
        # Create different types of memory
        store_memory_for_testing(self.test_story_id, 'character', 'hero_stats', 'Strength: 18, Wisdom: 16')
        store_memory_for_testing(self.test_story_id, 'inventory', 'weapons', 'Magic Sword, Shield of Protection')
        store_memory_for_testing(self.test_story_id, 'world', 'current_area', 'Dragon Lair')
        
        # Search with memory type filter
        results = self.engine.search_all("sword memtype:inventory")
        
        # Should find the inventory memory
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata['memory_type'], 'inventory')


if __name__ == '__main__':
    unittest.main()

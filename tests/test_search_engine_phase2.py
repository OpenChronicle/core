"""
Test suite for OpenChronicle Full-Text Search (FTS5) System - Phase 2 Features.

This test suite covers:
- Advanced query parsing (wildcards, proximity, complex operators)
- Search caching and performance optimization
- Search history and saved searches
- Search result export capabilities
- Performance monitoring and statistics
"""

import unittest
import os
import tempfile
import shutil
import json
from datetime import datetime
import sys

# Add the parent directory to the path so we can import our modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.database import init_database, check_fts_support, execute_insert
from core.search_engine import SearchEngine, SearchQuery, SearchHistory, SavedSearch
from core.scene_logger import save_scene

def store_memory_for_testing(story_id, memory_type, key, value):
    """Helper function to store memory for testing purposes."""
    execute_insert(story_id, '''
        INSERT INTO memory (story_id, type, key, value, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (story_id, memory_type, key, f'"{value}"', 
          datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))


class TestAdvancedQueryParsing(unittest.TestCase):
    """Test advanced query parsing features."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_advanced"
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
    
    def test_wildcard_parsing(self):
        """Test parsing of wildcard queries."""
        query = self.engine.parse_query("cast* ancient ?oor")
        
        self.assertEqual(len(query.wildcards), 2)
        self.assertIn("cast*", query.wildcards)
        self.assertIn("?oor", query.wildcards)
    
    def test_proximity_search_parsing(self):
        """Test parsing of proximity searches."""
        query = self.engine.parse_query("castle NEAR/5 door")
        
        self.assertEqual(len(query.proximity_searches), 1)
        self.assertEqual(query.proximity_searches[0], ("castle", "door", 5))
    
    def test_sort_order_parsing(self):
        """Test parsing of sort orders."""
        query = self.engine.parse_query("castle sort:date")
        
        self.assertEqual(query.sort_order, "date")
        self.assertNotIn("sort", query.filters)
    
    def test_limit_parsing(self):
        """Test parsing of result limits."""
        query = self.engine.parse_query("castle limit:25")
        
        self.assertEqual(query.limit, 25)
        self.assertNotIn("limit", query.filters)
    
    def test_complex_query_parsing(self):
        """Test parsing of complex queries with multiple features."""
        query = self.engine.parse_query(
            'castle AND "ancient door" cast* type:scene sort:date limit:20'
        )
        
        self.assertIn("castle", query.terms)
        self.assertIn("ancient door", query.quoted_phrases)
        self.assertIn("cast*", query.wildcards)
        self.assertIn("AND", query.operators)
        self.assertEqual(query.filters["type"], "scene")
        self.assertEqual(query.sort_order, "date")
        self.assertEqual(query.limit, 20)


class TestSearchCaching(unittest.TestCase):
    """Test search caching and performance features."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_caching"
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Initialize database
        init_database(self.test_story_id)
        
        # Check if FTS5 is supported
        if not check_fts_support():
            self.skipTest("FTS5 is not supported in this SQLite version")
        
        # Create SearchEngine with small cache for testing
        self.engine = SearchEngine(self.test_story_id, cache_size=3)
        
        # Create test data
        save_scene(
            self.test_story_id,
            "I explore the ancient castle",
            "You approach the massive stone fortress",
            scene_label="Castle Entry"
        )
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_search_caching(self):
        """Test that search results are cached."""
        # First search
        results1 = self.engine.search_all("castle")
        
        # Second search should use cache
        results2 = self.engine.search_all("castle")
        
        # Results should be identical
        self.assertEqual(len(results1), len(results2))
        self.assertEqual(self.engine.performance_stats['cache_hits'], 1)
        self.assertEqual(self.engine.performance_stats['total_queries'], 2)
    
    def test_cache_size_limit(self):
        """Test that cache size is limited."""
        # Fill cache beyond limit
        for i in range(5):
            self.engine.search_all(f"query{i}")
        
        # Cache should be limited to configured size
        self.assertLessEqual(len(self.engine.query_cache), 3)
    
    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        # Perform search to populate cache
        self.engine.search_all("castle")
        self.assertGreater(len(self.engine.query_cache), 0)
        
        # Clear cache
        self.engine.clear_cache()
        self.assertEqual(len(self.engine.query_cache), 0)
    
    def test_performance_tracking(self):
        """Test performance statistics tracking."""
        # Perform some searches
        self.engine.search_all("castle")
        self.engine.search_all("door")
        
        stats = self.engine.get_performance_stats()
        
        self.assertEqual(stats['total_queries'], 2)
        self.assertGreater(stats['avg_query_time'], 0)
        self.assertGreater(stats['total_query_time'], 0)
        self.assertGreaterEqual(stats['cache_hit_rate'], 0)


class TestSearchHistory(unittest.TestCase):
    """Test search history functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_history"
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
        save_scene(
            self.test_story_id,
            "I explore the ancient castle",
            "You approach the massive stone fortress",
            scene_label="Castle Entry"
        )
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_search_history_recording(self):
        """Test that search history is recorded."""
        # Perform searches
        self.engine.search_all("castle")
        self.engine.search_all("door")
        
        # Check history
        history = self.engine.get_search_history()
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].query, "castle")
        self.assertEqual(history[1].query, "door")
        self.assertIsInstance(history[0].timestamp, datetime)
        self.assertGreater(history[0].execution_time, 0)
    
    def test_search_history_limit(self):
        """Test that search history is limited."""
        # Perform many searches
        for i in range(105):
            self.engine.search_all(f"query{i}")
        
        # History should be limited
        history = self.engine.get_search_history()
        self.assertEqual(len(self.engine.search_history), 100)
    
    def test_clear_search_history(self):
        """Test clearing search history."""
        # Perform searches
        self.engine.search_all("castle")
        self.engine.search_all("door")
        
        # Clear history
        self.engine.clear_search_history()
        
        # History should be empty
        history = self.engine.get_search_history()
        self.assertEqual(len(history), 0)


class TestSavedSearches(unittest.TestCase):
    """Test saved searches functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_saved"
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
        save_scene(
            self.test_story_id,
            "I explore the ancient castle",
            "You approach the massive stone fortress",
            scene_label="Castle Entry"
        )
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_save_search(self):
        """Test saving a search."""
        # Save a search
        self.engine.save_search("Castle Search", "castle ancient", {"type": "scene"})
        
        # Retrieve saved search
        saved_search = self.engine.get_saved_search("Castle Search")
        
        self.assertIsNotNone(saved_search)
        self.assertEqual(saved_search.name, "Castle Search")
        self.assertEqual(saved_search.query, "castle ancient")
        self.assertEqual(saved_search.filters["type"], "scene")
        self.assertEqual(saved_search.use_count, 1)
    
    def test_list_saved_searches(self):
        """Test listing saved searches."""
        # Save multiple searches
        self.engine.save_search("Search 1", "castle")
        self.engine.save_search("Search 2", "door")
        
        # List saved searches
        saved_searches = self.engine.list_saved_searches()
        
        self.assertEqual(len(saved_searches), 2)
        search_names = [s.name for s in saved_searches]
        self.assertIn("Search 1", search_names)
        self.assertIn("Search 2", search_names)
    
    def test_delete_saved_search(self):
        """Test deleting a saved search."""
        # Save a search
        self.engine.save_search("Test Search", "castle")
        
        # Delete the search
        result = self.engine.delete_saved_search("Test Search")
        
        self.assertTrue(result)
        self.assertIsNone(self.engine.get_saved_search("Test Search"))
    
    def test_execute_saved_search(self):
        """Test executing a saved search."""
        # Save a search
        self.engine.save_search("Castle Search", "castle", {"type": "scene"})
        
        # Execute the saved search
        results = self.engine.execute_saved_search("Castle Search")
        
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].content_type, "scene")


class TestSearchSuggestions(unittest.TestCase):
    """Test search suggestion functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_suggestions"
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
        save_scene(
            self.test_story_id,
            "I explore the ancient castle",
            "You approach the massive stone fortress",
            scene_label="Castle Entry"
        )
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_search_suggestions_from_history(self):
        """Test getting search suggestions from history."""
        # Perform searches to populate history
        self.engine.search_all("castle ancient")
        self.engine.search_all("castle door")
        
        # Get suggestions
        suggestions = self.engine.get_search_suggestions("castle")
        
        self.assertGreater(len(suggestions), 0)
        self.assertIn("castle ancient", suggestions)
        self.assertIn("castle door", suggestions)
    
    def test_search_suggestions_from_saved_searches(self):
        """Test getting search suggestions from saved searches."""
        # Save searches
        self.engine.save_search("Castle Search", "castle exploration")
        self.engine.save_search("Castle Quest", "castle quest")
        
        # Get suggestions
        suggestions = self.engine.get_search_suggestions("castle")
        
        self.assertGreater(len(suggestions), 0)
        self.assertIn("castle exploration", suggestions)
        self.assertIn("castle quest", suggestions)


class TestSearchResultExport(unittest.TestCase):
    """Test search result export functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_export"
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
        save_scene(
            self.test_story_id,
            "I explore the ancient castle",
            "You approach the massive stone fortress",
            scene_label="Castle Entry"
        )
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_json_export(self):
        """Test exporting search results as JSON."""
        # Perform search
        results = self.engine.search_all("castle")
        
        # Export as JSON
        json_export = self.engine.export_search_results(results, 'json')
        
        # Verify JSON structure
        exported_data = json.loads(json_export)
        self.assertIsInstance(exported_data, list)
        self.assertGreater(len(exported_data), 0)
        
        # Check required fields
        result_data = exported_data[0]
        required_fields = ['id', 'content_type', 'title', 'content', 'snippet', 'score']
        for field in required_fields:
            self.assertIn(field, result_data)
    
    def test_markdown_export(self):
        """Test exporting search results as Markdown."""
        # Perform search
        results = self.engine.search_all("castle")
        
        # Export as Markdown
        markdown_export = self.engine.export_search_results(results, 'markdown')
        
        # Verify Markdown structure
        self.assertIn("# Search Results", markdown_export)
        self.assertIn("## 1.", markdown_export)
        self.assertIn("**Type:**", markdown_export)
        self.assertIn("**Score:**", markdown_export)
    
    def test_csv_export(self):
        """Test exporting search results as CSV."""
        # Perform search
        results = self.engine.search_all("castle")
        
        # Export as CSV
        csv_export = self.engine.export_search_results(results, 'csv')
        
        # Verify CSV structure
        lines = csv_export.strip().split('\n')
        self.assertGreater(len(lines), 1)  # Header + at least one data row
        
        # Check header
        header = lines[0]
        self.assertIn("ID", header)
        self.assertIn("Content Type", header)
        self.assertIn("Title", header)
    
    def test_unsupported_export_format(self):
        """Test handling of unsupported export formats."""
        # Perform search
        results = self.engine.search_all("castle")
        
        # Try unsupported format
        with self.assertRaises(ValueError):
            self.engine.export_search_results(results, 'xml')


class TestSortingAndFiltering(unittest.TestCase):
    """Test advanced sorting and filtering features."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_story_id = "test_story_sorting"
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
        
        # Create test data with different timestamps
        save_scene(
            self.test_story_id,
            "I explore the ancient castle",
            "You approach the massive stone fortress",
            scene_label="Castle Entry"
        )
        
        save_scene(
            self.test_story_id,
            "I examine the castle door",
            "The door is made of ancient oak",
            scene_label="Door Investigation"
        )
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_relevance_sorting(self):
        """Test sorting by relevance (default)."""
        results = self.engine.search_all("castle sort:relevance")
        
        # Results should be sorted by score (ascending for BM25)
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i].score, results[i + 1].score)
    
    def test_date_sorting(self):
        """Test sorting by date."""
        results = self.engine.search_all("castle sort:date")
        
        # Results should be sorted by timestamp (descending)
        for i in range(len(results) - 1):
            if results[i].timestamp and results[i + 1].timestamp:
                self.assertGreaterEqual(results[i].timestamp, results[i + 1].timestamp)
    
    def test_title_sorting(self):
        """Test sorting by title."""
        results = self.engine.search_all("castle sort:title")
        
        # Results should be sorted by title (ascending)
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i].title.lower(), results[i + 1].title.lower())
    
    def test_custom_limit(self):
        """Test custom result limits."""
        results = self.engine.search_all("castle limit:1")
        
        self.assertEqual(len(results), 1)


if __name__ == '__main__':
    unittest.main()

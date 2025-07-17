"""
OpenChronicle Testing Patterns

This file demonstrates standard testing patterns for OpenChronicle modules.
Use these patterns to ensure consistent and comprehensive testing.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Example imports for testing
from core.database import DatabaseManager
from core.memory_manager import MemoryManager
from core.story_loader import StoryLoader


class TestDatabaseIntegration:
    """Pattern for testing database integration"""
    
    @pytest.fixture
    def temp_db(self):
        """Temporary database for testing"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_file.close()
        
        yield temp_file.name
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    @pytest.fixture
    def db_manager(self, temp_db):
        """Database manager with temporary database"""
        return DatabaseManager("test_story", db_path=temp_db)
    
    def test_database_initialization(self, db_manager):
        """Test database initialization"""
        assert db_manager.story_id == "test_story"
        assert db_manager.db_path.exists()
        
        # Test table creation
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        
        # Verify table exists
        result = db_manager.fetch_one("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='test_table'
        """)
        assert result is not None
    
    def test_database_operations(self, db_manager):
        """Test basic database operations"""
        # Create test table
        db_manager.execute_query("""
            CREATE TABLE test_data (
                id INTEGER PRIMARY KEY,
                key TEXT,
                value TEXT
            )
        """)
        
        # Test insert
        db_manager.execute_query(
            "INSERT INTO test_data (key, value) VALUES (?, ?)",
            ("test_key", "test_value")
        )
        
        # Test fetch
        result = db_manager.fetch_one(
            "SELECT * FROM test_data WHERE key = ?",
            ("test_key",)
        )
        assert result['key'] == "test_key"
        assert result['value'] == "test_value"
        
        # Test update
        db_manager.execute_query(
            "UPDATE test_data SET value = ? WHERE key = ?",
            ("updated_value", "test_key")
        )
        
        # Verify update
        result = db_manager.fetch_one(
            "SELECT value FROM test_data WHERE key = ?",
            ("test_key",)
        )
        assert result['value'] == "updated_value"


class TestStorypackIntegration:
    """Pattern for testing storypack loading and validation"""
    
    @pytest.fixture
    def temp_storypack(self):
        """Create temporary storypack structure"""
        temp_dir = tempfile.mkdtemp()
        storypack_path = Path(temp_dir) / "test_story"
        storypack_path.mkdir()
        
        # Create meta.yaml
        meta_content = """
title: "Test Story"
description: "A test story"
author: "Test Author"
default_model: "mock"
fallback_chain: ["mock"]
nsfw_flags: false
"""
        (storypack_path / "meta.yaml").write_text(meta_content)
        
        # Create directories
        (storypack_path / "characters").mkdir()
        (storypack_path / "canon").mkdir()
        (storypack_path / "memory").mkdir()
        
        # Create test character
        char_content = """
{
  "name": "Test Character",
  "role": "protagonist",
  "personality": {"traits": ["brave", "curious"]},
  "style_block": {
    "voice": "Confident and direct",
    "tone": "Optimistic"
  }
}
"""
        (storypack_path / "characters" / "test_char.json").write_text(char_content)
        
        # Create test canon
        canon_content = "# Test Canon\n\nThis is test world information."
        (storypack_path / "canon" / "test_world.md").write_text(canon_content)
        
        yield storypack_path
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_storypack_loading(self, temp_storypack):
        """Test storypack loading"""
        loader = StoryLoader(str(temp_storypack))
        
        # Test meta loading
        meta = loader.load_meta()
        assert meta['title'] == "Test Story"
        assert meta['author'] == "Test Author"
        assert meta['default_model'] == "mock"
        
        # Test character loading
        characters = loader.load_characters()
        assert len(characters) == 1
        assert characters[0]['name'] == "Test Character"
        assert characters[0]['role'] == "protagonist"
        
        # Test canon loading
        canon = loader.load_canon()
        assert len(canon) == 1
        assert "test_world.md" in canon
        assert "This is test world information" in canon["test_world.md"]
    
    def test_storypack_validation(self, temp_storypack):
        """Test storypack validation"""
        loader = StoryLoader(str(temp_storypack))
        
        # Test valid storypack
        is_valid, errors = loader.validate()
        assert is_valid
        assert len(errors) == 0
        
        # Test invalid storypack (remove meta.yaml)
        (temp_storypack / "meta.yaml").unlink()
        is_valid, errors = loader.validate()
        assert not is_valid
        assert any("meta.yaml" in error for error in errors)


class TestLLMIntegration:
    """Pattern for testing LLM provider integration"""
    
    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response"""
        return {
            "choices": [
                {
                    "message": {
                        "content": "This is a test response from the LLM.",
                        "role": "assistant"
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120
            }
        }
    
    @patch('openai.ChatCompletion.create')
    def test_openai_integration(self, mock_openai, mock_llm_response):
        """Test OpenAI integration"""
        from core.model_adapter import ModelAdapter
        
        mock_openai.return_value = mock_llm_response
        
        adapter = ModelAdapter("openai")
        response = adapter.generate_response("Test prompt")
        
        assert response.content == "This is a test response from the LLM."
        assert response.tokens_used == 120
        mock_openai.assert_called_once()
    
    def test_model_fallback(self):
        """Test model fallback logic"""
        from core.model_adapter import ModelAdapter
        
        # Mock primary model failure
        with patch('core.model_adapter.OpenAIProvider.generate') as mock_primary:
            mock_primary.side_effect = Exception("Primary model failed")
            
            # Mock fallback model success
            with patch('core.model_adapter.OllamaProvider.generate') as mock_fallback:
                mock_fallback.return_value = Mock(
                    content="Fallback response",
                    tokens_used=50
                )
                
                adapter = ModelAdapter("openai", fallback_chain=["ollama"])
                response = adapter.generate_response("Test prompt")
                
                assert response.content == "Fallback response"
                assert response.tokens_used == 50
                mock_primary.assert_called_once()
                mock_fallback.assert_called_once()


class TestMemoryManagement:
    """Pattern for testing memory management"""
    
    @pytest.fixture
    def memory_manager(self, temp_db):
        """Memory manager with temporary database"""
        return MemoryManager("test_story", db_path=temp_db)
    
    def test_memory_storage_retrieval(self, memory_manager):
        """Test memory storage and retrieval"""
        # Test storing memory
        memory_data = {
            "character_states": {
                "hero": {"health": 100, "location": "tavern"}
            },
            "world_flags": {
                "tavern_visited": True,
                "quest_started": False
            }
        }
        
        memory_manager.store_memory("scene_001", memory_data)
        
        # Test retrieving memory
        retrieved = memory_manager.get_memory("scene_001")
        assert retrieved == memory_data
        
        # Test updating memory
        updated_data = {
            "character_states": {
                "hero": {"health": 90, "location": "forest"}
            },
            "world_flags": {
                "tavern_visited": True,
                "quest_started": True
            }
        }
        
        memory_manager.store_memory("scene_002", updated_data)
        
        # Test memory history
        history = memory_manager.get_memory_history(limit=2)
        assert len(history) == 2
        assert history[0]['scene_id'] == "scene_002"
        assert history[1]['scene_id'] == "scene_001"
    
    def test_memory_rollback(self, memory_manager):
        """Test memory rollback functionality"""
        # Create memory snapshots
        memory_manager.store_memory("scene_001", {"stage": 1})
        memory_manager.store_memory("scene_002", {"stage": 2})
        memory_manager.store_memory("scene_003", {"stage": 3})
        
        # Test rollback to scene_002
        memory_manager.rollback_to_scene("scene_002")
        
        current_memory = memory_manager.get_current_memory()
        assert current_memory["stage"] == 2
        
        # Verify scene_003 is no longer in history
        history = memory_manager.get_memory_history()
        scene_ids = [h['scene_id'] for h in history]
        assert "scene_003" not in scene_ids
        assert "scene_002" in scene_ids
        assert "scene_001" in scene_ids


class TestContentAnalysis:
    """Pattern for testing content analysis"""
    
    def test_content_classification(self):
        """Test content classification"""
        from core.content_analyzer import ContentAnalyzer
        
        analyzer = ContentAnalyzer()
        
        # Test different content types
        test_cases = [
            ("Hello, how are you?", "greeting"),
            ("I attack the goblin with my sword!", "action"),
            ("Tell me about the ancient prophecy.", "inquiry"),
            ("Let's go to the tavern.", "navigation")
        ]
        
        for content, expected_type in test_cases:
            result = analyzer.classify_content(content)
            assert result.content_type == expected_type
    
    def test_nsfw_detection(self):
        """Test NSFW content detection"""
        from core.content_analyzer import ContentAnalyzer
        
        analyzer = ContentAnalyzer()
        
        # Test safe content
        safe_content = "The hero explores the dungeon."
        result = analyzer.analyze_content(safe_content)
        assert not result.nsfw_detected
        
        # Test potentially unsafe content
        unsafe_content = "Explicit content example here"
        result = analyzer.analyze_content(unsafe_content)
        # This would depend on your actual NSFW detection implementation
        # assert result.nsfw_detected
    
    def test_token_optimization(self):
        """Test token optimization"""
        from core.content_analyzer import ContentAnalyzer
        
        analyzer = ContentAnalyzer()
        
        # Test content optimization
        long_content = "This is a very long piece of content that should be optimized for token usage. " * 100
        
        optimized = analyzer.optimize_for_tokens(long_content, max_tokens=100)
        
        # Verify optimization
        original_tokens = analyzer.count_tokens(long_content)
        optimized_tokens = analyzer.count_tokens(optimized)
        
        assert optimized_tokens <= 100
        assert optimized_tokens < original_tokens
        assert len(optimized) > 0  # Ensure content wasn't completely removed


# Test Configuration
@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "test_story_id": "test_story_12345",
        "temp_db_path": ":memory:",
        "mock_responses": {
            "greeting": "Hello! How can I help you today?",
            "action": "The action unfolds dramatically!",
            "inquiry": "Here's what you need to know..."
        }
    }


# Integration Test Examples
class TestFullIntegration:
    """Full integration tests"""
    
    def test_complete_scene_flow(self, temp_storypack, temp_db):
        """Test complete scene generation flow"""
        # This would test the full pipeline:
        # User input → Content analysis → Memory lookup → Context building → 
        # LLM generation → Memory update → Scene logging
        
        # Mock the LLM response
        with patch('core.model_adapter.ModelAdapter.generate_response') as mock_llm:
            mock_llm.return_value = Mock(
                content="The tavern is warm and welcoming.",
                tokens_used=25
            )
            
            # Initialize all components
            story_loader = StoryLoader(str(temp_storypack))
            memory_manager = MemoryManager("test_story", db_path=temp_db)
            
            # Test the flow
            user_input = "I enter the tavern."
            
            # This would be the actual integration test
            # result = process_user_input(user_input, story_loader, memory_manager)
            # assert result.scene_content == "The tavern is warm and welcoming."
            # assert result.memory_updated
            # assert result.scene_logged


# Helper Functions for Testing
def create_test_storypack(temp_dir: Path, story_name: str) -> Path:
    """Helper to create test storypack structure"""
    storypack_path = temp_dir / story_name
    storypack_path.mkdir()
    
    # Create required directories
    for dir_name in ['characters', 'canon', 'memory']:
        (storypack_path / dir_name).mkdir()
    
    # Create minimal meta.yaml
    meta_content = f"""
title: "{story_name}"
description: "Test story"
author: "Test"
default_model: "mock"
"""
    (storypack_path / "meta.yaml").write_text(meta_content)
    
    return storypack_path


def assert_valid_scene_output(scene_data: Dict[str, Any]):
    """Helper to validate scene output structure"""
    required_fields = ['scene_id', 'content', 'timestamp', 'memory_snapshot']
    
    for field in required_fields:
        assert field in scene_data, f"Missing required field: {field}"
    
    assert isinstance(scene_data['content'], str)
    assert len(scene_data['content']) > 0
    assert isinstance(scene_data['memory_snapshot'], dict)


def mock_llm_provider(provider_name: str, responses: Dict[str, str]):
    """Helper to mock LLM provider responses"""
    def mock_generate(prompt: str, **kwargs):
        # Simple keyword-based response selection
        for keyword, response in responses.items():
            if keyword.lower() in prompt.lower():
                return Mock(
                    content=response,
                    tokens_used=len(response.split()),
                    model_used=provider_name
                )
        
        # Default response
        return Mock(
            content="I don't understand that request.",
            tokens_used=7,
            model_used=provider_name
        )
    
    return mock_generate


# Example usage in tests
if __name__ == "__main__":
    # Run specific test patterns
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_database_operations"
    ])

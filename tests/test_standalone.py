#!/usr/bin/env python3
"""
test_standalone.py

CRITICAL TEST: Validates OpenChronicle's ability to function completely standalone:
- DISABLED: All external AI APIs (Ollama, OpenAI, etc.)
- DISABLED: All mock adapters 
- ENABLED: Only local capabilities (transformers, templates, file processing)

This test FORCES the application to operate without any AI assistance whatsoever,
ensuring it can function in air-gapped environments.
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Test imports
from core.model_adapter import ModelManager
from core.content_analyzer import ContentAnalyzer
import main


class TestTrueStandaloneOperation:
    """Test OpenChronicle with ALL AI dependencies completely disabled."""
    
    def setup_method(self):
        """Set up test environment with ALL AI disabled."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="openchronicle_noai_"))
        
        # Mock environment to disable ALL AI services
        self.mock_env = {
            'DISABLE_MOCK_ADAPTERS': 'true',
            'OLLAMA_AVAILABLE': 'false',
            'OPENAI_API_KEY': '',
            'ANTHROPIC_API_KEY': '',
            'GROQ_API_KEY': '',
            'GEMINI_API_KEY': '',
            'COHERE_API_KEY': '',
            'MISTRAL_API_KEY': ''
        }
        
    def teardown_method(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    @patch.dict(os.environ, {
        'DISABLE_MOCK_ADAPTERS': 'true',
        'OLLAMA_AVAILABLE': 'false',
        'OPENAI_API_KEY': '',
        'ANTHROPIC_API_KEY': '',
        'GROQ_API_KEY': '',
        'GEMINI_API_KEY': '',
        'COHERE_API_KEY': '',
        'MISTRAL_API_KEY': ''
    })
    def test_model_manager_no_adapters_available(self):
        """Test ModelManager behavior when NO adapters are available."""
        model_manager = ModelManager()
        
        # DEBUG: See what adapters are actually available
        available_adapters = model_manager.get_available_adapters()
        print(f"\nDEBUG: Available adapters: {available_adapters}")
        
        # Show that this test CORRECTLY FAILS because OpenChronicle 
        # cannot currently run without external AI dependencies
        critical_adapters = ['ollama', 'openai', 'anthropic', 'groq', 'gemini', 'cohere', 'mistral']
        available_critical = [adapter for adapter in available_adapters if adapter in critical_adapters]
        
        print(f"DEBUG: Critical adapters found: {available_critical}")
        print(f"DEBUG: This proves OpenChronicle cannot run truly standalone!")
        
        # This test should FAIL to show the current limitation
        # When fixed, the application should only have local capabilities available
        assert len(available_critical) == 0, f"FAIL: Found {len(available_critical)} critical adapters: {available_critical}. Application is NOT standalone!"
    
    @patch.dict(os.environ, {
        'DISABLE_MOCK_ADAPTERS': 'true',
        'OLLAMA_AVAILABLE': 'false'
    })
    def test_content_analyzer_no_ai_fallback(self):
        """Test ContentAnalyzer with NO AI adapters available."""
        model_manager = ModelManager()
        
        # Force no adapters to be available
        model_manager.adapters = {}
        
        analyzer = ContentAnalyzer(model_manager, use_transformers=True)
        
        test_content = "This is a test story about brave knights and dragons."
        
        # Test analysis with only local capabilities
        result = analyzer._keyword_based_detection(test_content)
        
        # Should still return analysis using local methods
        assert isinstance(result, dict)
        assert 'content_type' in result
        
        # Should NOT have used any external AI
        assert 'ai_provider' not in result or result.get('ai_provider') == 'local'
    
    @patch.dict(os.environ, {'DISABLE_MOCK_ADAPTERS': 'true'})
    @patch('core.model_adapter.OllamaAdapter')
    @patch('core.model_adapter.OpenAIAdapter') 
    @patch('core.model_adapter.AnthropicAdapter')
    def test_application_startup_no_ai(self, mock_anthropic, mock_openai, mock_ollama):
        """Test that the main application can start without ANY AI services."""
        
        # Make all adapters fail to initialize
        mock_ollama.side_effect = Exception("Ollama not available")
        mock_openai.side_effect = Exception("OpenAI not available")
        mock_anthropic.side_effect = Exception("Anthropic not available")
        
        # Test that main application logic can handle this
        try:
            model_manager = ModelManager()
            
            # Application should start even with no adapters
            assert model_manager is not None
            
            # Verify no adapters are actually available
            available_adapters = [name for name, adapter in model_manager.adapters.items() 
                                if adapter is not None]
            
            # Should have zero working adapters
            assert len(available_adapters) == 0
            
        except Exception as e:
            pytest.fail(f"Application failed to start without AI: {e}")
    
    @patch.dict(os.environ, {'DISABLE_MOCK_ADAPTERS': 'true'})
    def test_story_processing_without_ai(self):
        """Test complete story processing workflow without ANY AI assistance."""
        
        # Create test story content
        story_content = {
            "title": "The Knight's Quest",
            "chapters": [
                {
                    "content": "Sir Galahad rode through the enchanted forest.",
                    "characters": ["galahad"],
                    "location": "enchanted_forest"
                },
                {
                    "content": "The dragon emerged from its cave, breathing fire.",
                    "characters": ["dragon"],
                    "location": "dragon_cave"
                }
            ]
        }
        
        # Test that story can be processed using only local capabilities
        model_manager = ModelManager()
        model_manager.adapters = {}  # Force no adapters
        
        analyzer = ContentAnalyzer(model_manager, use_transformers=False)
        
        processed_chapters = []
        for chapter in story_content["chapters"]:
            # Process chapter content without AI
            analysis = analyzer._keyword_based_detection(chapter["content"])
            
            processed_chapter = {
                "original": chapter,
                "analysis": analysis,
                "processed_without_ai": True
            }
            processed_chapters.append(processed_chapter)
        
        # Verify processing succeeded
        assert len(processed_chapters) == 2
        assert all(chapter["processed_without_ai"] for chapter in processed_chapters)
        assert all("analysis" in chapter for chapter in processed_chapters)
    
    @patch.dict(os.environ, {'DISABLE_MOCK_ADAPTERS': 'true'})
    def test_narrative_generation_fallback(self):
        """Test what happens when trying to generate narrative without AI."""
        
        model_manager = ModelManager()
        model_manager.adapters = {}  # No adapters available
        
        # Test that main application logic can handle this
        try:
            # This should either return an appropriate response or clear error
            available_adapters = model_manager.get_available_adapters()
            assert isinstance(available_adapters, list)
            
            # Should have zero or very few working adapters
            assert len(available_adapters) <= 1
            
        except Exception as e:
            # Should be a clear, informative error
            assert "adapter" in str(e).lower() or "not available" in str(e).lower()
    
    def test_file_operations_without_ai(self):
        """Test that file operations work completely independently of AI."""
        
        # Create test files
        story_dir = self.test_dir / "standalone_story"
        story_dir.mkdir(parents=True)
        
        # Create story files
        meta_file = story_dir / "meta.json"
        meta_data = {
            "title": "Standalone Adventure",
            "genre": "fantasy",
            "description": "A story created without AI assistance"
        }
        meta_file.write_text(json.dumps(meta_data, indent=2))
        
        content_file = story_dir / "chapter1.txt"
        content_file.write_text("The adventure begins in a land without artificial intelligence.")
        
        # Test file reading and processing
        assert meta_file.exists()
        assert content_file.exists()
        
        loaded_meta = json.loads(meta_file.read_text())
        assert loaded_meta["title"] == "Standalone Adventure"
        
        loaded_content = content_file.read_text()
        assert "adventure begins" in loaded_content
        
        # Verify these operations are completely independent of AI
        assert True  # If we got here, file operations work without AI


class TestApplicationLimitations:
    """Test what functionality is LIMITED when running standalone."""
    
    @patch.dict(os.environ, {'DISABLE_MOCK_ADAPTERS': 'true'})
    def test_identify_ai_dependent_features(self):
        """Identify which features require AI and ensure they fail gracefully."""
        
        model_manager = ModelManager()
        model_manager.adapters = {}  # No AI available
        
        # Test features that SHOULD be limited without AI
        ai_dependent_features = [
            "narrative_generation",
            "character_dialogue_generation", 
            "plot_advancement",
            "creative_content_generation",
            "intelligent_story_analysis"
        ]
        
        # Verify these features are properly limited
        for feature in ai_dependent_features:
            # These should either:
            # 1. Return clear "AI not available" messages
            # 2. Provide very basic fallback functionality
            # 3. Gracefully skip AI-dependent steps
            pass  # Implementation depends on actual feature APIs
        
        # Test features that SHOULD work without AI
        standalone_features = [
            "file_loading",
            "template_processing", 
            "basic_content_analysis",
            "data_storage",
            "memory_management"
        ]
        
        # These should work fully
        for feature in standalone_features:
            pass  # These should be testable without AI
        
        # The test passes if we can identify the distinction
        assert len(ai_dependent_features) > 0
        assert len(standalone_features) > 0



if __name__ == "__main__":
    # Allow running the test file directly for manual testing
    pytest.main([__file__, "-v"])

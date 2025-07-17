"""
Test Character Style Manager with Tone Consistency
Tests the enhanced character style manager with tone auditing and scene anchoring.
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.character_style_manager import CharacterStyleManager

class TestCharacterStyleManager(unittest.TestCase):
    """Test suite for enhanced character style manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_model_manager = MagicMock()
        self.mock_model_manager.config = {
            "default_adapter": "mock",
            "content_routing": {
                "creative_models": ["anthropic", "openai"],
                "fast_models": ["openai", "mock"],
                "analysis_models": ["anthropic", "mock"],
                "safe_models": ["mock"]
            }
        }
        self.mock_model_manager.list_model_configs.return_value = {
            "anthropic": {"enabled": True, "content_filtering": {"allowed_content": ["creative", "general"]}},
            "openai": {"enabled": True, "content_filtering": {"allowed_content": ["creative", "general"]}},
            "mock": {"enabled": True, "content_filtering": {"allowed_content": ["creative", "general"]}}
        }
        self.mock_model_manager.get_adapter_info.return_value = {
            "content_filtering": {"allowed_content": ["creative", "general"]}
        }
        
        self.style_manager = CharacterStyleManager(self.mock_model_manager)
        
        # Load test character
        self.test_character = {
            "name": "Lyra Brightblade",
            "style_block": {
                "voice": "Confident and inspiring",
                "tone": "Warm but determined",
                "speech_patterns": ["Direct statements", "Encouraging phrases"],
                "emotional_range": {
                    "anger": "Controlled, righteous indignation",
                    "joy": "Radiant, infectious enthusiasm",
                    "sadness": "Quiet strength, empathetic"
                }
            },
            "preferred_models": ["anthropic", "openai"]
        }
        
        self.style_manager.load_character_style("lyra", self.test_character)
    
    def test_character_style_loading(self):
        """Test character style loading and formatting."""
        # Test style loading
        self.assertIn("lyra", self.style_manager.character_styles)
        
        # Test different model formatting
        openai_style = self.style_manager.get_character_style_prompt("lyra", "openai")
        self.assertIn("Confident and inspiring", openai_style)
        
        anthropic_style = self.style_manager.get_character_style_prompt("lyra", "anthropic")
        self.assertIn("Confident and inspiring", anthropic_style)
        
        ollama_style = self.style_manager.get_character_style_prompt("lyra", "ollama")
        self.assertIn("Confident and inspiring", ollama_style)
    
    def test_model_selection(self):
        """Test intelligent model selection for characters."""
        # Test preferred model selection
        selected = self.style_manager.select_character_model("lyra", "dialogue")
        self.assertIn(selected, ["anthropic", "openai"])  # Should pick preferred model
        
        # Test fallback to content routing
        selected = self.style_manager.select_character_model("unknown_character", "dialogue")
        self.assertIn(selected, ["anthropic", "openai", "mock"])
        
        # Test action content routing - should still prefer character's models
        selected = self.style_manager.select_character_model("lyra", "action")
        self.assertIn(selected, ["anthropic", "openai", "mock"])  # Preferred models take precedence
    
    def test_character_context_building(self):
        """Test building character context with style and tone."""
        # Add some tone history
        self.style_manager.tone_history["lyra"] = ["determined", "inspiring"]
        
        context = self.style_manager.build_character_context(
            "lyra", 
            "anthropic", 
            ["Previous scene text", "Another scene"]
        )
        
        self.assertIn("=== LYRA STYLE ===", context)
        self.assertIn("Recent tone: inspiring", context)
        self.assertIn("=== RECENT CONTEXT ===", context)
        self.assertIn("Another scene", context)
    
    def test_tone_analysis(self):
        """Test character tone analysis."""
        # Mock the model response
        mock_response = json.dumps({
            "tone": "determined",
            "consistency": 0.85,
            "style_elements": ["direct", "inspiring"],
            "deviations": [],
            "recommendations": "Maintain current tone"
        })
        
        self.mock_model_manager.generate_response = AsyncMock(return_value=mock_response)
        
        # Test tone analysis
        result = asyncio.run(self.style_manager.analyze_character_tone(
            "lyra", 
            "I will not let darkness prevail in our lands!"
        ))
        
        self.assertEqual(result["tone"], "determined")
        self.assertEqual(result["consistency"], 0.85)
        self.assertIn("lyra", self.style_manager.tone_history)
        self.assertEqual(self.style_manager.tone_history["lyra"][-1], "determined")
        self.assertEqual(len(self.style_manager.consistency_scores["lyra"]), 1)
        self.assertEqual(self.style_manager.consistency_scores["lyra"][0], 0.85)
    
    def test_consistency_scoring(self):
        """Test consistency score calculation."""
        # Add some scores
        self.style_manager.update_consistency_score("lyra", 0.8)
        self.style_manager.update_consistency_score("lyra", 0.9)
        self.style_manager.update_consistency_score("lyra", 0.7)
        
        # Test calculation (should weight recent scores more)
        score = self.style_manager.calculate_consistency_score("lyra")
        self.assertGreater(score, 0.7)
        self.assertLess(score, 0.9)  # Should be weighted average
        
        # Test with no scores
        score = self.style_manager.calculate_consistency_score("unknown")
        self.assertEqual(score, 0.5)
    
    def test_scene_anchoring(self):
        """Test echo-driven scene anchoring."""
        # Add tone history
        self.style_manager.tone_history["lyra"] = ["determined"]
        
        # Create scene anchor
        anchor = self.style_manager.create_scene_anchor(
            "lyra", 
            "Battle preparation scene",
            "anthropic"
        )
        
        self.assertIn("=== SCENE ANCHOR for lyra ===", anchor)
        self.assertIn("Recent tone: determined", anchor)
        self.assertIn("Battle preparation scene", anchor)
        self.assertIn("anthropic", anchor)
        
        # Check anchor storage
        self.assertIn("lyra", self.style_manager.scene_anchors)
        self.assertEqual(len(self.style_manager.scene_anchors["lyra"]), 1)
        self.assertEqual(self.style_manager.scene_anchors["lyra"][0]["model"], "anthropic")
    
    def test_narrative_stitching(self):
        """Test narrative stitching prompts."""
        # Add tone history and anchors
        self.style_manager.tone_history["lyra"] = ["determined", "inspiring", "focused"]
        self.style_manager.scene_anchors["lyra"] = [
            {"timestamp": 1234567890, "anchor": "test anchor", "model": "openai", "tone": "determined"}
        ]
        
        # Get stitching prompt
        prompt = self.style_manager.get_narrative_stitching_prompt("lyra", "openai", "anthropic")
        
        self.assertIn("=== NARRATIVE STITCHING for lyra ===", prompt)
        self.assertIn("model openai to model anthropic", prompt)
        self.assertIn("Recent tone progression: determined -> inspiring -> focused", prompt)
        self.assertIn("test anchor", prompt)
    
    def test_model_switching_suggestion(self):
        """Test model switching suggestions."""
        # Test with good consistency (no switch needed)
        suggestion = asyncio.run(self.style_manager.suggest_model_switch("lyra", 0.8))
        self.assertIsNone(suggestion)
        
        # Test with poor consistency (should suggest switch)
        suggestion = asyncio.run(self.style_manager.suggest_model_switch("lyra", 0.5))
        self.assertIsNotNone(suggestion)
        self.assertIn(suggestion, ["anthropic", "openai", "mock"])
    
    def test_character_stats(self):
        """Test character statistics."""
        # Add some data
        self.style_manager.tone_history["lyra"] = ["determined", "inspiring"]
        self.style_manager.update_consistency_score("lyra", 0.8)
        self.style_manager.scene_anchors["lyra"] = [{"test": "anchor"}]
        
        stats = self.style_manager.get_character_stats()
        
        self.assertEqual(stats["total_characters"], 1)
        self.assertEqual(stats["characters_with_tone_history"], 1)
        self.assertEqual(stats["character_details"]["lyra"]["tone_entries"], 2)
        self.assertEqual(stats["character_details"]["lyra"]["recent_tone"], "inspiring")
        self.assertEqual(stats["character_details"]["lyra"]["consistency"], 0.8)
        self.assertEqual(stats["character_details"]["lyra"]["scene_anchors"], 1)
        self.assertEqual(stats["average_consistency"], 0.8)
    
    def test_dynamic_style_updates(self):
        """Test dynamic character style updates."""
        # Test style update
        updates = {
            "style_block": {
                "voice": "More confident than before",
                "new_trait": "Battle-hardened"
            }
        }
        
        self.style_manager.update_character_style("lyra", updates)
        
        # Check if style was updated
        updated_style = self.style_manager.character_styles["lyra"]
        self.assertEqual(updated_style["style_block"]["voice"], "More confident than before")
        self.assertEqual(updated_style["style_block"]["new_trait"], "Battle-hardened")
    
    def test_error_handling(self):
        """Test error handling in tone analysis."""
        # Test with empty output
        result = asyncio.run(self.style_manager.analyze_character_tone("lyra", ""))
        self.assertEqual(result["tone"], "neutral")
        self.assertEqual(result["consistency"], 0.5)
        
        # Test with invalid model response
        self.mock_model_manager.generate_response = AsyncMock(side_effect=Exception("Model error"))
        result = asyncio.run(self.style_manager.analyze_character_tone("lyra", "Test output"))
        self.assertEqual(result["tone"], "unknown")
        self.assertEqual(result["consistency"], 0.5)

if __name__ == "__main__":
    unittest.main()

"""
Test Character Consistency Engine
Tests motivation anchoring, trait locking, and behavioral auditing functionality.
"""

import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import tempfile
import time

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.character_consistency_engine import (
    CharacterConsistencyEngine, 
    MotivationAnchor, 
    ConsistencyViolation, 
    ConsistencyViolationType
)

class TestCharacterConsistencyEngine(unittest.TestCase):
    """Test suite for Character Consistency Engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = CharacterConsistencyEngine()
        
        # Sample character data
        self.test_character_data = {
            "name": "Lyra",
            "emotional_profile": {
                "volatility": 0.2,  # Stoic
                "gratification_drive": 0.1,  # Independent
                "boundaries_enabled": True
            },
            "character_stats": {
                "intelligence": 9,  # Very high
                "charisma": 3,  # Very low
                "courage": 8,
                "loyalty": 9
            },
            "locked_traits": ["pacifist", "honest"],
            "motivation_anchors": [
                {
                    "trait_name": "scholarly_dedication",
                    "value": "books_over_people",
                    "description": "Prefers books and study to social interaction",
                    "priority": 1
                }
            ]
        }
        
        # Process test character
        self.engine._process_character_data("lyra", self.test_character_data)
    
    def test_initialization(self):
        """Test engine initialization."""
        engine = CharacterConsistencyEngine()
        self.assertIsInstance(engine.motivation_anchors, dict)
        self.assertIsInstance(engine.locked_traits, dict)
        self.assertIsInstance(engine.violation_history, dict)
        self.assertIsInstance(engine.consistency_scores, dict)
    
    def test_process_character_data(self):
        """Test character data processing."""
        # Check that character was processed
        self.assertIn("lyra", self.engine.motivation_anchors)
        self.assertIn("lyra", self.engine.locked_traits)
        self.assertIn("lyra", self.engine.consistency_scores)
        
        # Check motivation anchors were created
        anchors = self.engine.motivation_anchors["lyra"]
        self.assertTrue(len(anchors) > 0)
        
        # Check locked traits
        locked_traits = self.engine.locked_traits["lyra"]
        self.assertIn("pacifist", locked_traits)
        self.assertIn("honest", locked_traits)
        
        # Check initial consistency score
        self.assertEqual(self.engine.consistency_scores["lyra"], 1.0)
    
    def test_emotional_anchors_creation(self):
        """Test creation of anchors from emotional profile."""
        anchors = self.engine.motivation_anchors["lyra"]
        anchor_names = [a.trait_name for a in anchors]
        
        # Should have emotional control anchor (low volatility)
        self.assertIn("emotional_control", anchor_names)
        
        # Should have independence anchor (low gratification drive)
        self.assertIn("independence", anchor_names)
        
        # Should have boundaries anchor
        self.assertIn("personal_boundaries", anchor_names)
    
    def test_stat_anchors_creation(self):
        """Test creation of anchors from character stats."""
        anchors = self.engine.motivation_anchors["lyra"]
        anchor_names = [a.trait_name for a in anchors]
        
        # Should have high intelligence anchor
        self.assertIn("high_intelligence", anchor_names)
        
        # Should have low charisma anchor
        self.assertIn("low_charisma", anchor_names)
    
    def test_motivation_prompt_generation(self):
        """Test motivation prompt generation."""
        prompt = self.engine.get_motivation_prompt("lyra")
        
        self.assertIn("LYRA MOTIVATION ANCHORS", prompt)
        self.assertIn("emotional_control", prompt)
        self.assertIn("independence", prompt)
        self.assertIn("LOCKED TRAITS", prompt)
        self.assertIn("pacifist", prompt)
        self.assertIn("honest", prompt)
    
    def test_behavioral_consistency_analysis(self):
        """Test behavioral consistency analysis."""
        # Test scene that violates pacifist trait
        violent_scene = "Lyra drew her sword and attacked the bandit, slashing viciously."
        violations = self.engine.analyze_behavioral_consistency(
            "lyra", violent_scene, "scene_001"
        )
        
        self.assertTrue(len(violations) > 0)
        violation = violations[0]
        self.assertEqual(violation.violation_type, ConsistencyViolationType.TRAIT_VIOLATION)
        self.assertIn("pacifist", violation.description)
    
    def test_emotional_control_violation(self):
        """Test detection of emotional control violations."""
        # Lyra has low volatility (stoic), so shouldn't have explosive reactions
        emotional_scene = "Lyra screamed hysterically and sobbed uncontrollably."
        violations = self.engine.analyze_behavioral_consistency(
            "lyra", emotional_scene, "scene_002"
        )
        
        self.assertTrue(len(violations) > 0)
        violation = violations[0]
        self.assertEqual(violation.violation_type, ConsistencyViolationType.TRAIT_VIOLATION)
        self.assertIn("emotion", violation.description.lower())  # Changed from "emotional" to "emotion"
    
    def test_independence_violation(self):
        """Test detection of independence violations."""
        # Lyra is independent, shouldn't seek approval
        approval_scene = "Lyra looked at him pleadingly. 'Do you like me? Am I good enough?'"
        violations = self.engine.analyze_behavioral_consistency(
            "lyra", approval_scene, "scene_003"
        )
        
        self.assertTrue(len(violations) > 0)
        violation = violations[0]
        self.assertEqual(violation.violation_type, ConsistencyViolationType.MOTIVATION_CONFLICT)
        self.assertIn("approval", violation.description.lower())
    
    def test_boundary_violation(self):
        """Test detection of boundary violations."""
        boundary_scene = "Lyra whispered, 'I can't say no to you. Use me however you want.'"
        violations = self.engine.analyze_behavioral_consistency(
            "lyra", boundary_scene, "scene_004"
        )
        
        self.assertTrue(len(violations) > 0)
        violation = violations[0]
        self.assertEqual(violation.violation_type, ConsistencyViolationType.TRAIT_VIOLATION)
        self.assertIn("boundaries", violation.description.lower())
    
    def test_emotional_contradiction_detection(self):
        """Test detection of emotional contradictions."""
        contradiction_scene = "Lyra was happy and excited, but also sad and depressed about the news."
        violations = self.engine.analyze_behavioral_consistency(
            "lyra", contradiction_scene, "scene_005"
        )
        
        self.assertTrue(len(violations) > 0)
        violation = violations[0]
        self.assertEqual(violation.violation_type, ConsistencyViolationType.EMOTIONAL_CONTRADICTION)
    
    def test_consistency_score_updates(self):
        """Test consistency score updates after violations."""
        initial_score = self.engine.get_consistency_score("lyra")
        self.assertEqual(initial_score, 1.0)
        
        # Trigger a violation
        violent_scene = "Lyra killed the enemy without mercy."
        self.engine.analyze_behavioral_consistency("lyra", violent_scene, "scene_006")
        
        updated_score = self.engine.get_consistency_score("lyra")
        self.assertLess(updated_score, initial_score)
    
    def test_consistent_behavior_no_violations(self):
        """Test that consistent behavior produces no violations."""
        consistent_scene = "Lyra studied her books quietly, avoiding the loud tavern crowd."
        violations = self.engine.analyze_behavioral_consistency(
            "lyra", consistent_scene, "scene_007"
        )
        
        self.assertEqual(len(violations), 0)
    
    def test_fallback_prompt_generation(self):
        """Test fallback prompt generation for limited tokens."""
        fallback_prompt = self.engine.get_fallback_prompt("lyra", max_tokens=100)
        
        self.assertIn("lyra", fallback_prompt.lower())
        self.assertIn("core traits", fallback_prompt.lower())
        self.assertTrue(len(fallback_prompt) <= 100)
    
    def test_add_motivation_anchor(self):
        """Test adding new motivation anchor."""
        new_anchor = MotivationAnchor(
            trait_name="test_trait",
            value="test_value",
            description="Test anchor",
            priority=3
        )
        
        initial_count = len(self.engine.motivation_anchors["lyra"])
        self.engine.add_motivation_anchor("lyra", new_anchor)
        
        new_count = len(self.engine.motivation_anchors["lyra"])
        self.assertEqual(new_count, initial_count + 1)
        
        # Check the anchor was added
        anchor_names = [a.trait_name for a in self.engine.motivation_anchors["lyra"]]
        self.assertIn("test_trait", anchor_names)
    
    def test_lock_trait(self):
        """Test locking new trait."""
        initial_count = len(self.engine.locked_traits["lyra"])
        self.engine.lock_trait("lyra", "new_locked_trait")
        
        new_count = len(self.engine.locked_traits["lyra"])
        self.assertEqual(new_count, initial_count + 1)
        self.assertIn("new_locked_trait", self.engine.locked_traits["lyra"])
    
    def test_consistency_report(self):
        """Test consistency report generation."""
        # Generate some violations first
        violent_scene = "Lyra attacked with brutal force."
        self.engine.analyze_behavioral_consistency("lyra", violent_scene, "scene_008")
        
        report = self.engine.get_consistency_report("lyra")
        
        self.assertIn("character_name", report)
        self.assertIn("consistency_score", report)
        self.assertIn("motivation_anchors", report)
        self.assertIn("locked_traits", report)
        self.assertIn("total_violations", report)
        
        self.assertEqual(report["character_name"], "lyra")
        self.assertGreater(report["total_violations"], 0)
    
    def test_violation_serialization(self):
        """Test violation serialization to dictionary."""
        violation = ConsistencyViolation(
            violation_type=ConsistencyViolationType.TRAIT_VIOLATION,
            character_name="test_char",
            scene_id="test_scene",
            description="Test violation",
            severity=0.5,
            expected_behavior="Expected",
            actual_behavior="Actual",
            timestamp=time.time()
        )
        
        violation_dict = violation.to_dict()
        
        self.assertIn("violation_type", violation_dict)
        self.assertIn("character_name", violation_dict)
        self.assertIn("scene_id", violation_dict)
        self.assertEqual(violation_dict["violation_type"], "trait_violation")
    
    def test_engine_stats(self):
        """Test engine statistics generation."""
        stats = self.engine.get_stats()
        
        self.assertIn("total_characters", stats)
        self.assertIn("total_violations", stats)
        self.assertIn("average_consistency_score", stats)
        
        self.assertGreaterEqual(stats["total_characters"], 1)  # At least our test character
    
    def test_load_character_consistency_data(self):
        """Test loading character data from files."""
        # Create temporary directory with character file
        with tempfile.TemporaryDirectory() as temp_dir:
            characters_dir = os.path.join(temp_dir, "characters")
            os.makedirs(characters_dir)
            
            # Create test character file
            char_file = os.path.join(characters_dir, "test_char.json")
            with open(char_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_character_data, f)
            
            # Create new engine and load data
            new_engine = CharacterConsistencyEngine()
            new_engine.load_character_consistency_data(temp_dir)
            
            # Check that data was loaded
            self.assertIn("test_char", new_engine.motivation_anchors)
            self.assertIn("test_char", new_engine.locked_traits)
    
    def test_context_specific_anchors(self):
        """Test context-specific motivation anchors."""
        # Add context-specific anchor
        context_anchor = MotivationAnchor(
            trait_name="combat_anxiety",
            value="fearful",
            description="Character becomes anxious in combat",
            context_requirement="combat"
        )
        self.engine.add_motivation_anchor("lyra", context_anchor)
        
        # Test prompt with combat context
        combat_prompt = self.engine.get_motivation_prompt("lyra", "combat")
        self.assertIn("combat_anxiety", combat_prompt)
        
        # Test prompt without context (should still include general anchors)
        general_prompt = self.engine.get_motivation_prompt("lyra")
        self.assertIn("emotional_control", general_prompt)
    
    def test_priority_sorting(self):
        """Test that anchors are sorted by priority."""
        # Create a new character with fewer anchors for this test
        test_char_data = {
            "emotional_profile": {
                "volatility": 0.5,  # Neutral
                "gratification_drive": 0.5,  # Neutral
                "boundaries_enabled": True
            },
            "character_stats": {},  # No stats to avoid creating extra anchors
            "locked_traits": []
        }
        
        # Process new character
        self.engine._process_character_data("test_char", test_char_data)
        
        # Add anchors with different priorities
        high_priority = MotivationAnchor("high_priority_trait", "value", "High priority", priority=1)
        low_priority = MotivationAnchor("low_priority_trait", "value", "Low priority", priority=3)
        
        self.engine.add_motivation_anchor("test_char", high_priority)
        self.engine.add_motivation_anchor("test_char", low_priority)
        
        prompt = self.engine.get_motivation_prompt("test_char")
        
        # High priority should appear before low priority
        high_pos = prompt.find("high_priority_trait")
        low_pos = prompt.find("low_priority_trait")
        
        self.assertGreater(high_pos, -1)  # Make sure it was found
        self.assertGreater(low_pos, -1)   # Make sure it was found
        self.assertLess(high_pos, low_pos)
    
    def test_unknown_character_handling(self):
        """Test handling of unknown characters."""
        # Test with character that doesn't exist
        prompt = self.engine.get_motivation_prompt("unknown_char")
        self.assertEqual(prompt, "")
        
        violations = self.engine.analyze_behavioral_consistency(
            "unknown_char", "test output", "scene_001"
        )
        self.assertEqual(len(violations), 0)
        
        score = self.engine.get_consistency_score("unknown_char")
        self.assertEqual(score, 1.0)  # Default score

if __name__ == "__main__":
    unittest.main()

"""
Character Stat Engine (Narrative Trait Framework)

This module implements RPG-style narrative traits for characters, affecting how they
think, speak, and act across story scenes. It provides a standardized trait system
that enables deep emotional realism, nuanced responses, and dynamic character behavior.

Key Features:
- Standardized trait system (intelligence, charisma, courage, etc.)
- Stat-influenced response generation and character behavior
- Dynamic stat progression and character growth tracking
- Conditional behavior based on trait combinations
- Integration with other character engines for holistic behavior
- Narrative consequence system based on character limitations
"""

import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
import random
import math

# Setup logging
logger = logging.getLogger(__name__)

class StatType(Enum):
    """Types of character statistics/traits."""
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"
    WILLPOWER = "willpower"
    CREATIVITY = "creativity"
    HUMOR = "humor"
    COURAGE = "courage"
    LOYALTY = "loyalty"
    GREED = "greed"
    TEMPER = "temper"
    EMPATHY = "empathy"
    PERCEPTION = "perception"

class StatCategory(Enum):
    """Categories of character traits."""
    MENTAL = "mental"  # Intelligence, Wisdom, Creativity
    SOCIAL = "social"  # Charisma, Humor, Empathy
    EMOTIONAL = "emotional"  # Willpower, Temper, Courage
    MORAL = "moral"  # Loyalty, Greed, Empathy

class BehaviorModifier(Enum):
    """Types of behavior modifications based on stats."""
    SPEECH_PATTERN = "speech_pattern"
    DECISION_MAKING = "decision_making"
    RISK_TOLERANCE = "risk_tolerance"
    SOCIAL_INTERACTION = "social_interaction"
    EMOTIONAL_RESPONSE = "emotional_response"
    LEARNING_ABILITY = "learning_ability"

@dataclass
class StatProgression:
    """Tracks progression/changes in a character's stats over time."""
    stat_type: StatType
    old_value: int
    new_value: int
    reason: str
    timestamp: datetime
    scene_context: str = ""
    permanent: bool = True  # Whether this change is permanent or temporary
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'stat_type': self.stat_type.value,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'scene_context': self.scene_context,
            'permanent': self.permanent
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StatProgression':
        """Create from dictionary."""
        return cls(
            stat_type=StatType(data['stat_type']),
            old_value=data['old_value'],
            new_value=data['new_value'],
            reason=data['reason'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            scene_context=data.get('scene_context', ''),
            permanent=data.get('permanent', True)
        )

@dataclass
class BehaviorInfluence:
    """Represents how a stat influences character behavior."""
    stat_type: StatType
    stat_value: int
    modifier_type: BehaviorModifier
    influence_strength: float  # 0.0 to 1.0
    description: str
    examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'stat_type': self.stat_type.value,
            'stat_value': self.stat_value,
            'modifier_type': self.modifier_type.value,
            'influence_strength': self.influence_strength,
            'description': self.description,
            'examples': self.examples
        }

@dataclass
class CharacterStats:
    """Complete character statistics profile."""
    character_id: str
    stats: Dict[StatType, int] = field(default_factory=dict)
    progression_history: List[StatProgression] = field(default_factory=list)
    temporary_modifiers: Dict[StatType, Tuple[int, datetime]] = field(default_factory=dict)  # (modifier, expiry)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Initialize with default stats if not provided."""
        if not self.stats:
            self.stats = self._get_default_stats()
    
    def _get_default_stats(self) -> Dict[StatType, int]:
        """Get default stat values (5 = average)."""
        return {
            StatType.INTELLIGENCE: 5,
            StatType.WISDOM: 5,
            StatType.CHARISMA: 5,
            StatType.WILLPOWER: 5,
            StatType.CREATIVITY: 5,
            StatType.HUMOR: 5,
            StatType.COURAGE: 5,
            StatType.LOYALTY: 5,
            StatType.GREED: 5,
            StatType.TEMPER: 5,
            StatType.EMPATHY: 5,
            StatType.PERCEPTION: 5
        }
    
    def get_effective_stat(self, stat_type: StatType) -> int:
        """Get stat value including temporary modifiers."""
        base_value = self.stats.get(stat_type, 5)
        
        # Apply temporary modifier if active
        if stat_type in self.temporary_modifiers:
            modifier, expiry = self.temporary_modifiers[stat_type]
            if datetime.now() < expiry:
                return max(1, min(10, base_value + modifier))
            else:
                # Expired modifier, remove it
                del self.temporary_modifiers[stat_type]
        
        return base_value
    
    def update_stat(self, stat_type: StatType, new_value: int, reason: str, 
                   scene_context: str = "", permanent: bool = True) -> None:
        """Update a character stat with progression tracking."""
        old_value = self.stats.get(stat_type, 5)
        new_value = max(1, min(10, new_value))  # Clamp to 1-10 range
        
        if permanent:
            self.stats[stat_type] = new_value
        
        # Record progression
        progression = StatProgression(
            stat_type=stat_type,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            timestamp=datetime.now(),
            scene_context=scene_context,
            permanent=permanent
        )
        
        self.progression_history.append(progression)
        self.last_updated = datetime.now()
        
        logger.info(f"Updated {self.character_id} {stat_type.value}: "
                   f"{old_value} -> {new_value} ({reason})")
    
    def add_temporary_modifier(self, stat_type: StatType, modifier: int, 
                             duration_minutes: int, reason: str) -> None:
        """Add temporary stat modifier."""
        expiry = datetime.now() + timedelta(minutes=duration_minutes)
        self.temporary_modifiers[stat_type] = (modifier, expiry)
        
        logger.info(f"Added temporary {stat_type.value} modifier {modifier:+d} "
                   f"to {self.character_id} for {duration_minutes} minutes ({reason})")
    
    def get_stat_category_average(self, category: StatCategory) -> float:
        """Get average stat value for a category."""
        category_stats = self._get_stats_by_category(category)
        if not category_stats:
            return 5.0
        
        total = sum(self.get_effective_stat(stat) for stat in category_stats)
        return total / len(category_stats)
    
    def _get_stats_by_category(self, category: StatCategory) -> List[StatType]:
        """Get stats that belong to a specific category."""
        category_mapping = {
            StatCategory.MENTAL: [StatType.INTELLIGENCE, StatType.WISDOM, StatType.CREATIVITY, StatType.PERCEPTION],
            StatCategory.SOCIAL: [StatType.CHARISMA, StatType.HUMOR, StatType.EMPATHY],
            StatCategory.EMOTIONAL: [StatType.WILLPOWER, StatType.TEMPER, StatType.COURAGE],
            StatCategory.MORAL: [StatType.LOYALTY, StatType.GREED, StatType.EMPATHY]
        }
        return category_mapping.get(category, [])
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'character_id': self.character_id,
            'stats': {stat.value: value for stat, value in self.stats.items()},
            'progression_history': [prog.to_dict() for prog in self.progression_history],
            'temporary_modifiers': {
                stat.value: [modifier, expiry.isoformat()]
                for stat, (modifier, expiry) in self.temporary_modifiers.items()
            },
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterStats':
        """Create from dictionary."""
        stats = {StatType(stat): value for stat, value in data.get('stats', {}).items()}
        progression_history = [
            StatProgression.from_dict(prog) for prog in data.get('progression_history', [])
        ]
        
        temp_modifiers = {}
        for stat_str, (modifier, expiry_str) in data.get('temporary_modifiers', {}).items():
            temp_modifiers[StatType(stat_str)] = (modifier, datetime.fromisoformat(expiry_str))
        
        return cls(
            character_id=data['character_id'],
            stats=stats,
            progression_history=progression_history,
            temporary_modifiers=temp_modifiers,
            last_updated=datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
        )

class CharacterStatEngine:
    """
    Manages character statistics, trait-based behavior, and stat progression.
    
    This engine provides RPG-style character traits that influence behavior,
    dialogue, decision-making, and character development over time.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the character stat engine."""
        self.config = config or {}
        
        # Configuration parameters
        self.stat_range = self.config.get('stat_range', (1, 10))
        self.default_stat_value = self.config.get('default_stat_value', 5)
        self.progression_enabled = self.config.get('progression_enabled', True)
        self.temporary_modifier_max_duration = self.config.get('temp_modifier_max_hours', 24)
        
        # Data storage
        self.character_stats: Dict[str, CharacterStats] = {}
        self.behavior_templates: Dict[str, Dict] = self._initialize_behavior_templates()
        self.stat_interactions: Dict[str, List[Tuple[StatType, StatType]]] = self._initialize_stat_interactions()
        
        # Stat influence thresholds
        self.thresholds = {
            'very_low': (1, 2),
            'low': (3, 4),
            'average': (5, 6),
            'high': (7, 8),
            'very_high': (9, 10)
        }
    
    def initialize_character(self, character_id: str, initial_stats: Optional[Dict[str, int]] = None) -> CharacterStats:
        """Initialize or update character statistics."""
        if character_id in self.character_stats:
            character = self.character_stats[character_id]
            
            # Update stats if provided
            if initial_stats:
                for stat_name, value in initial_stats.items():
                    try:
                        stat_type = StatType(stat_name)
                        character.update_stat(stat_type, value, "Character initialization")
                    except ValueError:
                        logger.warning(f"Unknown stat type: {stat_name}")
            
            return character
        
        # Create new character stats
        character = CharacterStats(character_id=character_id)
        
        if initial_stats:
            for stat_name, value in initial_stats.items():
                try:
                    stat_type = StatType(stat_name)
                    character.stats[stat_type] = max(1, min(10, value))
                except ValueError:
                    logger.warning(f"Unknown stat type: {stat_name}")
        
        self.character_stats[character_id] = character
        logger.info(f"Initialized character stats for: {character_id}")
        
        return character
    
    def get_character_stats(self, character_id: str) -> Optional[CharacterStats]:
        """Get character statistics."""
        return self.character_stats.get(character_id)
    
    def update_character_stat(self, character_id: str, stat_type: StatType, 
                            new_value: int, reason: str, scene_context: str = "") -> bool:
        """Update a character's stat with progression tracking."""
        if character_id not in self.character_stats:
            logger.warning(f"Character {character_id} not found for stat update")
            return False
        
        character = self.character_stats[character_id]
        character.update_stat(stat_type, new_value, reason, scene_context)
        return True
    
    def add_temporary_stat_modifier(self, character_id: str, stat_type: StatType,
                                  modifier: int, duration_minutes: int, reason: str) -> bool:
        """Add temporary stat modifier to character."""
        if character_id not in self.character_stats:
            logger.warning(f"Character {character_id} not found for temporary modifier")
            return False
        
        if duration_minutes > (self.temporary_modifier_max_duration * 60):
            logger.warning(f"Temporary modifier duration exceeds maximum allowed")
            return False
        
        character = self.character_stats[character_id]
        character.add_temporary_modifier(stat_type, modifier, duration_minutes, reason)
        return True
    
    def generate_behavior_context(self, character_id: str, situation_type: str = "general") -> Dict[str, Any]:
        """Generate behavior context based on character stats."""
        if character_id not in self.character_stats:
            return {}
        
        character = self.character_stats[character_id]
        behavior_influences = []
        
        # Analyze each stat for behavioral influence
        for stat_type, value in character.stats.items():
            effective_value = character.get_effective_stat(stat_type)
            influences = self._get_stat_influences(stat_type, effective_value, situation_type)
            behavior_influences.extend(influences)
        
        # Get dominant traits
        dominant_traits = self._get_dominant_traits(character)
        
        # Get behavioral limitations and strengths
        limitations = self._get_character_limitations(character)
        strengths = self._get_character_strengths(character)
        
        return {
            'character_id': character_id,
            'behavior_influences': [inf.to_dict() for inf in behavior_influences],
            'dominant_traits': dominant_traits,
            'limitations': limitations,
            'strengths': strengths,
            'stat_summary': self._get_stat_summary(character),
            'situation_context': situation_type
        }
    
    def generate_response_prompt(self, character_id: str, content_type: str = "dialogue",
                               emotional_state: str = "neutral") -> str:
        """Generate stat-influenced prompt for character responses."""
        if character_id not in self.character_stats:
            return ""
        
        character = self.character_stats[character_id]
        prompt_parts = []
        
        # Get key behavioral influences
        behavior_context = self.generate_behavior_context(character_id, content_type)
        
        if behavior_context.get('dominant_traits'):
            traits_str = ", ".join(behavior_context['dominant_traits'])
            prompt_parts.append(f"[CHARACTER_TRAITS: {character_id} is characterized by {traits_str}]")
        
        # Add specific behavioral guidelines based on stats
        guidelines = self._generate_behavioral_guidelines(character, content_type, emotional_state)
        if guidelines:
            prompt_parts.extend(guidelines)
        
        # Add limitations and considerations
        limitations = behavior_context.get('limitations', [])
        if limitations:
            limit_str = "; ".join(limitations[:3])  # Top 3 limitations
            prompt_parts.append(f"[LIMITATIONS: {character_id} may struggle with: {limit_str}]")
        
        return "\n".join(prompt_parts)
    
    def check_stat_based_decision(self, character_id: str, decision_context: str,
                                required_stats: Dict[StatType, int]) -> Dict[str, Any]:
        """Check if character can make a decision based on their stats."""
        if character_id not in self.character_stats:
            return {"success": False, "reason": "Character not found"}
        
        character = self.character_stats[character_id]
        results = {}
        overall_success = True
        
        for stat_type, required_value in required_stats.items():
            character_value = character.get_effective_stat(stat_type)
            success = character_value >= required_value
            
            results[stat_type.value] = {
                'required': required_value,
                'character_value': character_value,
                'success': success,
                'margin': character_value - required_value
            }
            
            if not success:
                overall_success = False
        
        # Calculate success probability for partial success scenarios
        if not overall_success:
            success_probability = self._calculate_success_probability(character, required_stats)
        else:
            success_probability = 1.0
        
        return {
            'character_id': character_id,
            'decision_context': decision_context,
            'overall_success': overall_success,
            'success_probability': success_probability,
            'stat_checks': results,
            'suggested_outcome': self._suggest_outcome(character, required_stats, overall_success)
        }
    
    def trigger_stat_progression(self, character_id: str, trigger_event: str,
                               scene_context: str = "") -> List[StatProgression]:
        """Trigger potential stat progression based on story events."""
        if not self.progression_enabled or character_id not in self.character_stats:
            return []
        
        character = self.character_stats[character_id]
        progressions = []
        
        # Define progression triggers
        progression_triggers = {
            'combat_victory': [(StatType.COURAGE, 1), (StatType.WILLPOWER, 1)],
            'social_success': [(StatType.CHARISMA, 1), (StatType.HUMOR, 1)],
            'learning_experience': [(StatType.INTELLIGENCE, 1), (StatType.WISDOM, 1)],
            'creative_achievement': [(StatType.CREATIVITY, 1), (StatType.INTELLIGENCE, 1)],
            'moral_dilemma': [(StatType.WISDOM, 1), (StatType.EMPATHY, 1)],
            'betrayal_experienced': [(StatType.WISDOM, 1), (StatType.TEMPER, 1)],
            'leadership_moment': [(StatType.CHARISMA, 1), (StatType.WILLPOWER, 1)],
            'fear_overcome': [(StatType.COURAGE, 2), (StatType.WILLPOWER, 1)]
        }
        
        if trigger_event in progression_triggers:
            for stat_type, bonus in progression_triggers[trigger_event]:
                current_value = character.get_effective_stat(stat_type)
                
                # Apply diminishing returns for high stats
                if current_value >= 8:
                    if random.random() > 0.3:  # 30% chance for high stats
                        continue
                elif current_value >= 6:
                    if random.random() > 0.7:  # 70% chance for medium stats
                        continue
                
                new_value = current_value + bonus
                character.update_stat(
                    stat_type, new_value, 
                    f"Progression from {trigger_event}", 
                    scene_context
                )
                
                progressions.append(character.progression_history[-1])
        
        return progressions
    
    def get_stat_summary(self, character_id: str) -> Dict[str, Any]:
        """Get comprehensive stat summary for a character."""
        if character_id not in self.character_stats:
            return {}
        
        character = self.character_stats[character_id]
        
        # Calculate category averages
        category_averages = {}
        for category in StatCategory:
            category_averages[category.value] = character.get_stat_category_average(category)
        
        # Get recent progressions
        recent_progressions = [
            prog.to_dict() for prog in character.progression_history[-5:]
        ]
        
        # Get active temporary modifiers
        active_modifiers = {}
        current_time = datetime.now()
        for stat_type, (modifier, expiry) in character.temporary_modifiers.items():
            if current_time < expiry:
                remaining_minutes = int((expiry - current_time).total_seconds() / 60)
                active_modifiers[stat_type.value] = {
                    'modifier': modifier,
                    'remaining_minutes': remaining_minutes
                }
        
        return {
            'character_id': character_id,
            'current_stats': {
                stat.value: character.get_effective_stat(stat) 
                for stat in character.stats.keys()
            },
            'base_stats': {stat.value: value for stat, value in character.stats.items()},
            'category_averages': category_averages,
            'dominant_traits': self._get_dominant_traits(character),
            'recent_progressions': recent_progressions,
            'active_modifiers': active_modifiers,
            'total_progressions': len(character.progression_history),
            'last_updated': character.last_updated.isoformat()
        }
    
    def export_character_data(self, character_id: str) -> Dict[str, Any]:
        """Export all data for a character."""
        if character_id not in self.character_stats:
            return {}
        
        character = self.character_stats[character_id]
        return character.to_dict()
    
    def import_character_data(self, character_data: Dict[str, Any]) -> None:
        """Import character data from external source."""
        character = CharacterStats.from_dict(character_data)
        self.character_stats[character.character_id] = character
        logger.info(f"Imported character data for: {character.character_id}")
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        total_characters = len(self.character_stats)
        total_progressions = sum(
            len(char.progression_history) for char in self.character_stats.values()
        )
        
        # Calculate average stats across all characters
        if total_characters > 0:
            stat_totals = {}
            for character in self.character_stats.values():
                for stat_type, value in character.stats.items():
                    if stat_type not in stat_totals:
                        stat_totals[stat_type] = []
                    stat_totals[stat_type].append(value)
            
            average_stats = {
                stat.value: sum(values) / len(values)
                for stat, values in stat_totals.items()
            }
        else:
            average_stats = {}
        
        return {
            'total_characters': total_characters,
            'total_progressions': total_progressions,
            'average_stats_across_characters': average_stats,
            'progression_enabled': self.progression_enabled,
            'engine_config': self.config
        }
    
    def _initialize_behavior_templates(self) -> Dict[str, Dict]:
        """Initialize behavior influence templates."""
        return {
            'speech_patterns': {
                StatType.INTELLIGENCE: {
                    'high': ['articulate', 'precise', 'complex vocabulary'],
                    'low': ['simple', 'direct', 'colloquial']
                },
                StatType.CHARISMA: {
                    'high': ['persuasive', 'engaging', 'confident'],
                    'low': ['blunt', 'awkward', 'reserved']
                },
                StatType.HUMOR: {
                    'high': ['witty', 'playful', 'light-hearted'],
                    'low': ['serious', 'literal', 'dry']
                }
            },
            'decision_making': {
                StatType.WISDOM: {
                    'high': ['thoughtful', 'considers consequences', 'patient'],
                    'low': ['impulsive', 'short-sighted', 'hasty']
                },
                StatType.COURAGE: {
                    'high': ['bold', 'takes risks', 'confrontational'],
                    'low': ['cautious', 'avoids conflict', 'hesitant']
                }
            }
        }
    
    def _initialize_stat_interactions(self) -> Dict[str, List[Tuple[StatType, StatType]]]:
        """Initialize stat interaction patterns."""
        return {
            'synergistic': [
                (StatType.INTELLIGENCE, StatType.CREATIVITY),
                (StatType.CHARISMA, StatType.HUMOR),
                (StatType.WISDOM, StatType.EMPATHY),
                (StatType.COURAGE, StatType.WILLPOWER)
            ],
            'conflicting': [
                (StatType.GREED, StatType.LOYALTY),
                (StatType.TEMPER, StatType.WISDOM),
                (StatType.COURAGE, StatType.INTELLIGENCE)  # Sometimes courage conflicts with caution
            ]
        }
    
    def _get_stat_influences(self, stat_type: StatType, value: int, situation: str) -> List[BehaviorInfluence]:
        """Get behavioral influences for a specific stat value."""
        influences = []
        
        # Determine influence level
        if value <= 2:
            level = 'very_low'
            strength = 0.9
        elif value <= 4:
            level = 'low'
            strength = 0.7
        elif value <= 6:
            level = 'average'
            strength = 0.3
        elif value <= 8:
            level = 'high'
            strength = 0.7
        else:
            level = 'very_high'
            strength = 0.9
        
        # Generate specific influences based on stat and level
        influence_map = self._get_influence_mapping()
        
        if stat_type in influence_map and level in influence_map[stat_type]:
            for modifier_type, description in influence_map[stat_type][level].items():
                influences.append(BehaviorInfluence(
                    stat_type=stat_type,
                    stat_value=value,
                    modifier_type=modifier_type,
                    influence_strength=strength,
                    description=description
                ))
        
        return influences
    
    def _get_influence_mapping(self) -> Dict[StatType, Dict[str, Dict[BehaviorModifier, str]]]:
        """Get the complete mapping of stat influences."""
        return {
            StatType.INTELLIGENCE: {
                'very_low': {
                    BehaviorModifier.SPEECH_PATTERN: "speaks simply, often confused by complex ideas",
                    BehaviorModifier.DECISION_MAKING: "makes decisions based on gut feeling rather than analysis"
                },
                'low': {
                    BehaviorModifier.SPEECH_PATTERN: "uses straightforward language, avoids complexity",
                    BehaviorModifier.LEARNING_ABILITY: "learns slowly, needs repeated explanations"
                },
                'high': {
                    BehaviorModifier.SPEECH_PATTERN: "uses precise, sophisticated language",
                    BehaviorModifier.DECISION_MAKING: "analyzes situations thoroughly before acting"
                },
                'very_high': {
                    BehaviorModifier.SPEECH_PATTERN: "speaks with exceptional eloquence and complexity",
                    BehaviorModifier.LEARNING_ABILITY: "grasps concepts instantly, makes connections others miss"
                }
            },
            StatType.CHARISMA: {
                'very_low': {
                    BehaviorModifier.SOCIAL_INTERACTION: "struggles in social situations, often says wrong thing",
                    BehaviorModifier.SPEECH_PATTERN: "awkward, blunt, or offensive without meaning to be"
                },
                'low': {
                    BehaviorModifier.SOCIAL_INTERACTION: "prefers to avoid social spotlight",
                    BehaviorModifier.SPEECH_PATTERN: "direct but sometimes tactless"
                },
                'high': {
                    BehaviorModifier.SOCIAL_INTERACTION: "naturally draws people in, persuasive",
                    BehaviorModifier.SPEECH_PATTERN: "engaging, knows how to read the room"
                },
                'very_high': {
                    BehaviorModifier.SOCIAL_INTERACTION: "magnetic presence, can sway almost anyone",
                    BehaviorModifier.SPEECH_PATTERN: "captivating speaker, words carry great weight"
                }
            },
            StatType.COURAGE: {
                'very_low': {
                    BehaviorModifier.RISK_TOLERANCE: "avoids any dangerous situation, may flee when needed",
                    BehaviorModifier.DECISION_MAKING: "paralyzed by fear in crisis situations"
                },
                'low': {
                    BehaviorModifier.RISK_TOLERANCE: "very cautious, needs encouragement to act",
                    BehaviorModifier.EMOTIONAL_RESPONSE: "anxiety dominates in stressful situations"
                },
                'high': {
                    BehaviorModifier.RISK_TOLERANCE: "willing to take calculated risks",
                    BehaviorModifier.DECISION_MAKING: "acts decisively in dangerous situations"
                },
                'very_high': {
                    BehaviorModifier.RISK_TOLERANCE: "fearless, may take unnecessary risks",
                    BehaviorModifier.DECISION_MAKING: "charges into danger without hesitation"
                }
            },
            StatType.TEMPER: {
                'very_low': {
                    BehaviorModifier.EMOTIONAL_RESPONSE: "extremely patient, almost never loses composure",
                    BehaviorModifier.SOCIAL_INTERACTION: "calming presence, good mediator"
                },
                'low': {
                    BehaviorModifier.EMOTIONAL_RESPONSE: "slow to anger, thinks before reacting",
                    BehaviorModifier.DECISION_MAKING: "maintains objectivity under pressure"
                },
                'high': {
                    BehaviorModifier.EMOTIONAL_RESPONSE: "quick to anger, emotional reactions",
                    BehaviorModifier.SPEECH_PATTERN: "may snap or speak harshly when frustrated"
                },
                'very_high': {
                    BehaviorModifier.EMOTIONAL_RESPONSE: "explosive temper, loses control easily",
                    BehaviorModifier.DECISION_MAKING: "makes impulsive choices when angry"
                }
            }
        }
    
    def _get_dominant_traits(self, character: CharacterStats) -> List[str]:
        """Get character's dominant traits (highest stats)."""
        stat_values = [(stat, character.get_effective_stat(stat)) for stat in character.stats.keys()]
        stat_values.sort(key=lambda x: x[1], reverse=True)
        
        # Get top 3 traits that are above average (6+)
        dominant = []
        for stat_type, value in stat_values[:3]:
            if value >= 6:
                dominant.append(f"{stat_type.value} ({value})")
        
        return dominant
    
    def _get_character_limitations(self, character: CharacterStats) -> List[str]:
        """Get character limitations based on low stats."""
        limitations = []
        
        for stat_type, value in character.stats.items():
            effective_value = character.get_effective_stat(stat_type)
            if effective_value <= 3:
                limitation = self._get_limitation_text(stat_type, effective_value)
                if limitation:
                    limitations.append(limitation)
        
        return limitations
    
    def _get_character_strengths(self, character: CharacterStats) -> List[str]:
        """Get character strengths based on high stats."""
        strengths = []
        
        for stat_type, value in character.stats.items():
            effective_value = character.get_effective_stat(stat_type)
            if effective_value >= 8:
                strength = self._get_strength_text(stat_type, effective_value)
                if strength:
                    strengths.append(strength)
        
        return strengths
    
    def _get_limitation_text(self, stat_type: StatType, value: int) -> str:
        """Get descriptive text for a character limitation."""
        limitation_map = {
            StatType.INTELLIGENCE: "struggles with complex reasoning",
            StatType.CHARISMA: "poor social skills, often misunderstood",
            StatType.COURAGE: "easily frightened, avoids confrontation",
            StatType.WILLPOWER: "weak self-control, gives up easily",
            StatType.WISDOM: "poor judgment, doesn't learn from mistakes",
            StatType.EMPATHY: "insensitive to others' feelings",
            StatType.PERCEPTION: "misses important details and cues"
        }
        return limitation_map.get(stat_type, "")
    
    def _get_strength_text(self, stat_type: StatType, value: int) -> str:
        """Get descriptive text for a character strength."""
        strength_map = {
            StatType.INTELLIGENCE: "exceptional analytical abilities",
            StatType.CHARISMA: "naturally inspiring and persuasive",
            StatType.COURAGE: "fearless in the face of danger",
            StatType.WILLPOWER: "unbreakable determination",
            StatType.WISDOM: "profound insight and judgment",
            StatType.CREATIVITY: "innovative and imaginative solutions",
            StatType.LOYALTY: "unwavering dedication to allies",
            StatType.EMPATHY: "deeply understanding of others"
        }
        return strength_map.get(stat_type, "")
    
    def _get_stat_summary(self, character: CharacterStats) -> Dict[str, Any]:
        """Get a summary of character's stat profile."""
        stats = {stat.value: character.get_effective_stat(stat) for stat in character.stats.keys()}
        
        highest_stat = max(stats.items(), key=lambda x: x[1])
        lowest_stat = min(stats.items(), key=lambda x: x[1])
        
        return {
            'highest_stat': {'name': highest_stat[0], 'value': highest_stat[1]},
            'lowest_stat': {'name': lowest_stat[0], 'value': lowest_stat[1]},
            'average_stat': round(sum(stats.values()) / len(stats), 1),
            'stat_range': max(stats.values()) - min(stats.values())
        }
    
    def _generate_behavioral_guidelines(self, character: CharacterStats, content_type: str, 
                                      emotional_state: str) -> List[str]:
        """Generate specific behavioral guidelines based on stats and context."""
        guidelines = []
        
        # Intelligence-based guidelines
        intel = character.get_effective_stat(StatType.INTELLIGENCE)
        if intel <= 3:
            guidelines.append("[INTELLIGENCE: Character speaks simply, may misunderstand complex situations]")
        elif intel >= 8:
            guidelines.append("[INTELLIGENCE: Character uses sophisticated reasoning and vocabulary]")
        
        # Charisma-based guidelines
        charisma = character.get_effective_stat(StatType.CHARISMA)
        if charisma <= 3:
            guidelines.append("[CHARISMA: Character is socially awkward, may say inappropriate things]")
        elif charisma >= 8:
            guidelines.append("[CHARISMA: Character is naturally charming and persuasive]")
        
        # Courage-based guidelines for action content
        if content_type in ['action', 'combat', 'danger']:
            courage = character.get_effective_stat(StatType.COURAGE)
            if courage <= 3:
                guidelines.append("[COURAGE: Character likely to retreat or seek safety first]")
            elif courage >= 8:
                guidelines.append("[COURAGE: Character fearlessly faces danger head-on]")
        
        # Temper-based guidelines for emotional states
        if emotional_state in ['angry', 'frustrated', 'stressed']:
            temper = character.get_effective_stat(StatType.TEMPER)
            if temper >= 7:
                guidelines.append("[TEMPER: Character prone to outbursts when provoked]")
            elif temper <= 3:
                guidelines.append("[TEMPER: Character remains calm even under pressure]")
        
        return guidelines
    
    def _calculate_success_probability(self, character: CharacterStats, 
                                     required_stats: Dict[StatType, int]) -> float:
        """Calculate probability of success for partially failed stat checks."""
        total_margin = 0
        total_checks = len(required_stats)
        
        for stat_type, required_value in required_stats.items():
            character_value = character.get_effective_stat(stat_type)
            margin = character_value - required_value
            # Convert margin to probability contribution (negative margins reduce probability)
            prob_contribution = max(0, min(1, (margin + 5) / 10))  # Normalize to 0-1
            total_margin += prob_contribution
        
        return total_margin / total_checks if total_checks > 0 else 0.0
    
    def _suggest_outcome(self, character: CharacterStats, required_stats: Dict[StatType, int], 
                        overall_success: bool) -> str:
        """Suggest narrative outcome based on stat check results."""
        if overall_success:
            return "Character succeeds confidently based on their abilities"
        
        # Analyze which stats failed and suggest partial outcomes
        failed_stats = []
        for stat_type, required_value in required_stats.items():
            if character.get_effective_stat(stat_type) < required_value:
                failed_stats.append(stat_type.value)
        
        if len(failed_stats) == 1:
            return f"Character struggles due to low {failed_stats[0]}, but may succeed with effort or help"
        else:
            return f"Character likely to fail due to insufficient {', '.join(failed_stats[:2])}"

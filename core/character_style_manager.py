"""
Character Style Manager with Dynamic Model Selection
Maintains character consistency across different LLM models.
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent.parent / "utilities"))
from logging_system import log_system_event, log_info, log_warning, log_error

class CharacterStyleManager:
    """Manages character style consistency across dynamic model switching."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.character_styles = {}
        self.model_adaptations = {}
        self.tone_history = {}
        
    def load_character_styles(self, story_path: str) -> Dict[str, Dict[str, Any]]:
        """Load character style blocks from story characters."""
        characters_dir = os.path.join(story_path, "characters")
        styles = {}
        
        if not os.path.exists(characters_dir):
            return styles
            
        for char_file in os.listdir(characters_dir):
            if char_file.endswith('.json'):
                char_name = char_file[:-5]  # Remove .json
                char_path = os.path.join(characters_dir, char_file)
                
                try:
                    with open(char_path, 'r', encoding='utf-8') as f:
                        char_data = json.load(f)
                        
                    if 'style_block' in char_data:
                        styles[char_name] = char_data['style_block']
                        log_info(f"Loaded style block for {char_name}")
                        
                except Exception as e:
                    log_error(f"Failed to load character style for {char_name}: {e}")
                    
        self.character_styles = styles
        return styles
    
    def get_character_style_prompt(self, character_name: str, model_name: str) -> str:
        """Get character style prompt adapted for specific model."""
        if character_name not in self.character_styles:
            return ""
            
        style = self.character_styles[character_name]
        model_config = self.model_manager.get_adapter_info(model_name)
        provider = model_config.get("provider", "").lower()
        
        # Adapt style prompt based on model provider
        if provider == "openai":
            return self._format_openai_style(style)
        elif provider == "anthropic":
            return self._format_anthropic_style(style)
        elif provider == "ollama":
            return self._format_ollama_style(style)
        else:
            return self._format_generic_style(style)
    
    def _format_openai_style(self, style: Dict[str, Any]) -> str:
        """Format style for OpenAI models."""
        parts = []
        
        if "voice" in style:
            parts.append(f"Voice: {style['voice']}")
        if "tone" in style:
            parts.append(f"Tone: {style['tone']}")
        if "syntax" in style:
            parts.append(f"Speech patterns: {style['syntax']}")
        if "personality" in style:
            parts.append(f"Personality: {style['personality']}")
            
        return "\\n".join(parts)
    
    def _format_anthropic_style(self, style: Dict[str, Any]) -> str:
        """Format style for Anthropic models."""
        parts = ["Character speaking style:"]
        
        for key, value in style.items():
            parts.append(f"- {key.title()}: {value}")
            
        return "\\n".join(parts)
    
    def _format_ollama_style(self, style: Dict[str, Any]) -> str:
        """Format style for Ollama models (more direct)."""
        parts = ["This character speaks with:"]
        
        for key, value in style.items():
            parts.append(f"{key}: {value}")
            
        return " ".join(parts)
    
    def _format_generic_style(self, style: Dict[str, Any]) -> str:
        """Generic style formatting."""
        return f"Character style: {json.dumps(style, indent=2)}"
    
    def select_character_model(self, character_name: str, content_type: str = "dialogue") -> str:
        """Select the best model for a specific character."""
        # Get character preferences if any
        character_style = self.character_styles.get(character_name, {})
        preferred_models = character_style.get("preferred_models", [])
        
        # Get available models
        available_models = self.model_manager.list_model_configs()
        enabled_models = [
            name for name, config in available_models.items()
            if config.get("enabled", True)
        ]
        
        # Try preferred models first
        for model in preferred_models:
            if model in enabled_models:
                log_info(f"Using preferred model {model} for {character_name}")
                return model
        
        # Fallback to content routing
        config = self.model_manager.config
        content_routing = config.get("content_routing", {})
        
        if content_type == "dialogue":
            candidates = content_routing.get("creative_models", [])
        elif content_type == "action":
            candidates = content_routing.get("fast_models", [])
        else:
            candidates = content_routing.get("safe_models", [])
        
        # Filter for enabled models
        enabled_candidates = [
            name for name in candidates 
            if name in enabled_models
        ]
        
        if enabled_candidates:
            selected = enabled_candidates[0]
            log_info(f"Selected {selected} for {character_name} {content_type}")
            return selected
        
        # Ultimate fallback
        return "mock"
    
    def build_character_context(self, character_name: str, model_name: str, 
                               recent_scenes: List[str] = None) -> str:
        """Build character context with style consistency."""
        context_parts = []
        
        # Add character style
        style_prompt = self.get_character_style_prompt(character_name, model_name)
        if style_prompt:
            context_parts.append(f"=== {character_name.upper()} STYLE ===")
            context_parts.append(style_prompt)
        
        # Add recent tone analysis if available
        if character_name in self.tone_history:
            recent_tone = self.tone_history[character_name][-1]
            context_parts.append(f"Recent tone: {recent_tone}")
        
        # Add scene anchoring
        if recent_scenes:
            context_parts.append("=== RECENT CONTEXT ===")
            context_parts.extend(recent_scenes[-2:])  # Last 2 scenes
        
        return "\\n\\n".join(context_parts)
    
    async def analyze_character_tone(self, character_name: str, output: str) -> Dict[str, Any]:
        """Analyze character output for tone consistency."""
        if not output.strip():
            return {"tone": "neutral", "consistency": 0.5}
        
        # Use analysis model for tone detection
        analysis_model = self._get_analysis_model()
        
        prompt = f"""Analyze the tone and style of this character dialogue:

Character: {character_name}
Output: "{output}"

Expected style: {json.dumps(self.character_styles.get(character_name, {}), indent=2)}

Provide analysis in JSON format:
{{
  "tone": "description of current tone",
  "consistency": 0.0-1.0 (how consistent with expected style),
  "style_elements": ["observed", "style", "elements"],
  "deviations": ["any", "style", "deviations"],
  "recommendations": "suggestions for improvement"
}}"""

        try:
            response = await self.model_manager.generate_response(
                prompt,
                adapter_name=analysis_model,
                max_tokens=256,
                temperature=0.1
            )
            
            analysis = json.loads(response)
            
            # Store tone history
            if character_name not in self.tone_history:
                self.tone_history[character_name] = []
            self.tone_history[character_name].append(analysis["tone"])
            
            # Keep only last 5 tone entries
            if len(self.tone_history[character_name]) > 5:
                self.tone_history[character_name] = self.tone_history[character_name][-5:]
            
            log_system_event("character_tone_analysis", 
                           f"{character_name}: {analysis['tone']} (consistency: {analysis['consistency']})")
            
            return analysis
            
        except Exception as e:
            log_error(f"Character tone analysis failed: {e}")
            return {"tone": "unknown", "consistency": 0.5}
    
    def _get_analysis_model(self) -> str:
        """Get the best model for tone analysis."""
        config = self.model_manager.config
        content_routing = config.get("content_routing", {})
        candidates = content_routing.get("analysis_models", ["mock"])
        
        # Get first enabled model
        available_models = self.model_manager.list_model_configs()
        for model in candidates:
            if available_models.get(model, {}).get("enabled", True):
                return model
        
        return "mock"
    
    async def suggest_model_switch(self, character_name: str, 
                                  consistency_score: float) -> Optional[str]:
        """Suggest model switch if character consistency is poor."""
        if consistency_score > 0.7:
            return None  # Good consistency, no switch needed
        
        # Get current model performance for this character
        current_model = self.get_current_character_model(character_name)
        
        # Try alternative models
        alternative_models = self._get_alternative_models(current_model)
        
        for alt_model in alternative_models:
            # Check if this model might be better for this character
            if self._model_suitable_for_character(alt_model, character_name):
                log_info(f"Suggesting model switch from {current_model} to {alt_model} for {character_name}")
                return alt_model
        
        return None
    
    def _get_alternative_models(self, current_model: str) -> List[str]:
        """Get alternative models to try."""
        all_models = self.model_manager.list_model_configs()
        alternatives = [
            name for name, config in all_models.items()
            if config.get("enabled", True) and name != current_model
        ]
        
        # Sort by preference (creative models first for characters)
        config = self.model_manager.config
        creative_models = config.get("content_routing", {}).get("creative_models", [])
        
        alternatives.sort(key=lambda x: 0 if x in creative_models else 1)
        return alternatives
    
    def _model_suitable_for_character(self, model_name: str, character_name: str) -> bool:
        """Check if a model is suitable for a character."""
        model_config = self.model_manager.get_adapter_info(model_name)
        
        # Check if model supports creative content
        content_filtering = model_config.get("content_filtering", {})
        allowed_content = content_filtering.get("allowed_content", [])
        
        return "creative" in allowed_content or "general" in allowed_content
    
    def get_current_character_model(self, character_name: str) -> str:
        """Get the currently used model for a character."""
        # This would track which model was last used for each character
        # For now, return the default
        return self.model_manager.config.get("default_adapter", "mock")
    
    def update_character_style(self, character_name: str, style_updates: Dict[str, Any]):
        """Update character style dynamically."""
        if character_name not in self.character_styles:
            self.character_styles[character_name] = {}
        
        self.character_styles[character_name].update(style_updates)
        
        log_system_event("character_style_update", 
                        f"Updated style for {character_name}: {style_updates}")
    
    def get_character_stats(self) -> Dict[str, Any]:
        """Get character consistency statistics."""
        stats = {
            "total_characters": len(self.character_styles),
            "characters_with_tone_history": len(self.tone_history),
            "average_consistency": 0.0,
            "character_details": {}
        }
        
        total_consistency = 0
        consistency_count = 0
        
        for char_name, tones in self.tone_history.items():
            if char_name in self.character_styles:
                # Calculate average consistency for this character
                # (This would need to be tracked during tone analysis)
                char_consistency = 0.8  # Placeholder
                total_consistency += char_consistency
                consistency_count += 1
                
                stats["character_details"][char_name] = {
                    "tone_entries": len(tones),
                    "recent_tone": tones[-1] if tones else "unknown",
                    "consistency": char_consistency
                }
        
        if consistency_count > 0:
            stats["average_consistency"] = total_consistency / consistency_count
        
        return stats

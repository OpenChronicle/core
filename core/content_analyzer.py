"""
Content Analysis Engine for OpenChronicle with Dynamic Model Routing.
Uses dynamic model selection to optimize content analysis and routing.
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
from pathlib import Path

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent.parent / "utilities"))
from logging_system import log_model_interaction, log_system_event, log_info, log_error

class ContentAnalyzer:
    """Analyzes user input and story content with dynamic model routing."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.analysis_cache = {}
        self.routing_rules = {}
        self.content_patterns = {}
        
    def get_best_analysis_model(self, content_type: str = "general") -> str:
        """Get the best model for content analysis based on dynamic configuration."""
        # Get content routing from registry
        config = self.model_manager.config
        content_routing = config.get("content_routing", {})
        
        # Select model based on content type
        if content_type == "nsfw":
            candidates = content_routing.get("nsfw_models", [])
        elif content_type == "creative":
            candidates = content_routing.get("creative_models", [])
        elif content_type == "analysis":
            candidates = content_routing.get("analysis_models", [])
        else:
            candidates = content_routing.get("safe_models", [])
            
        # Filter for enabled models
        enabled_models = [
            name for name in candidates 
            if self.model_manager.list_model_configs().get(name, {}).get("enabled", True)
        ]
        
        if not enabled_models:
            log_warning("No enabled models for content analysis, using fallback")
            return "mock"
            
        # Select the first available model (they're ordered by preference)
        selected = enabled_models[0]
        log_info(f"Selected {selected} for {content_type} content analysis")
        return selected
        
    def detect_content_type(self, user_input: str) -> str:
        """Detect content type to route to appropriate analysis model."""
        text_lower = user_input.lower()
        
        # NSFW content detection
        nsfw_keywords = [
            "explicit", "sexual", "adult", "mature", "intimate", "romantic",
            "kiss", "embrace", "seductive", "passionate", "desire"
        ]
        
        if any(keyword in text_lower for keyword in nsfw_keywords):
            return "nsfw"
            
        # Creative content detection
        creative_keywords = [
            "imagine", "create", "describe", "story", "scene", "character",
            "dialogue", "narrative", "plot", "setting", "atmosphere"
        ]
        
        if any(keyword in text_lower for keyword in creative_keywords):
            return "creative"
            
        # Analysis content detection
        analysis_keywords = [
            "analyze", "classify", "determine", "evaluate", "assess",
            "summarize", "explain", "interpret", "understand"
        ]
        
        if any(keyword in text_lower for keyword in analysis_keywords):
            return "analysis"
            
        return "general"
        
    async def analyze_user_input(self, user_input: str, story_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user input with dynamic model selection for optimal analysis.
        """
        # Detect content type for model routing
        content_type = self.detect_content_type(user_input)
        
        # Get the best model for this content type
        analysis_model = self.get_best_analysis_model(content_type)
        
        analysis_prompt = self._build_analysis_prompt(user_input, story_context)
        
        try:
            # Use dynamically selected model for analysis
            analysis_response = await self.model_manager.generate_response(
                analysis_prompt,
                adapter_name=analysis_model,
                story_id=story_context.get("story_id"),
                max_tokens=512,
                temperature=0.1  # Low temperature for consistent analysis
            )
            
            # Parse the structured analysis
            analysis = self._parse_analysis_response(analysis_response)
            
            # Add routing information
            analysis["content_type"] = content_type
            analysis["analysis_model"] = analysis_model
            analysis["routing_recommendation"] = self.recommend_generation_model(analysis)
            
            # Cache the analysis
            cache_key = hash(user_input + str(story_context.get("story_id", "")))
            self.analysis_cache[cache_key] = analysis
            
            log_system_event("content_analysis", 
                           f"Analyzed with {analysis_model}: {content_type} content")
            
            return analysis
            
        except Exception as e:
            log_error(f"Content analysis failed with {analysis_model}: {e}")
            # Fallback to basic analysis
            return self._basic_analysis_fallback(user_input, story_context)
    
    def recommend_generation_model(self, analysis: Dict[str, Any]) -> str:
        """Recommend the best model for content generation based on analysis."""
        content_type = analysis.get("content_type", "general")
        content_flags = analysis.get("content_flags", [])
        
        config = self.model_manager.config
        content_routing = config.get("content_routing", {})
        
        # Check for NSFW content
        if "nsfw" in content_flags or "mature" in content_flags:
            candidates = content_routing.get("nsfw_models", [])
        # Check for creative content
        elif content_type == "creative" or "creative" in content_flags:
            candidates = content_routing.get("creative_models", [])
        # Check for fast/simple responses
        elif "simple" in content_flags or "quick" in content_flags:
            candidates = content_routing.get("fast_models", [])
        else:
            candidates = content_routing.get("safe_models", [])
        
        # Filter for enabled models
        enabled_models = [
            name for name in candidates 
            if self.model_manager.list_model_configs().get(name, {}).get("enabled", True)
        ]
        
        if not enabled_models:
            log_warning("No enabled models for content generation, using fallback")
            return "mock"
        
        recommended = enabled_models[0]
        log_info(f"Recommended {recommended} for generation based on {content_type} analysis")
        return recommended
    
    def _basic_analysis_fallback(self, user_input: str, story_context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis when dynamic analysis fails."""
        content_type = self.detect_content_type(user_input)
        
        return {
            "content_type": content_type,
            "intent": "story_continuation",
            "content_flags": [],
            "routing_recommendation": self.get_best_analysis_model(content_type),
            "analysis_model": "fallback",
            "context_needed": ["memory", "canon"],
            "confidence": 0.5
        }
    
    def _build_analysis_prompt(self, user_input: str, story_context: Dict[str, Any]) -> str:
        """Build the analysis prompt for the local LLM."""
        
        story_title = story_context.get("meta", {}).get("title", "Unknown Story")
        characters = list(story_context.get("characters", {}).keys())
        
        prompt = f"""Analyze this user input for an interactive story system.

STORY CONTEXT:
Title: {story_title}
Known Characters: {', '.join(characters) if characters else 'None'}

USER INPUT: "{user_input}"

Provide analysis in this JSON format:
{{
  "content_type": "action|dialogue|description|question|command",
  "intent": "brief description of user intent",
  "entities": {{
    "characters": ["character names mentioned"],
    "locations": ["locations mentioned"],
    "items": ["items/objects mentioned"],
    "emotions": ["emotional tones detected"]
  }},
  "content_flags": {{
    "nsfw": false,
    "violence": false,
    "mature_themes": false,
    "emotional_intensity": "low|medium|high"
  }},
  "required_canon": ["suggested canon files to reference"],
  "memory_triggers": ["memory flags that should be activated"],
  "response_style": "narrative|descriptive|action|dialogue",
  "token_priority": "high|medium|low"
}}

Response (JSON only):"""
        
        return prompt
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the structured analysis response from the local LLM."""
        try:
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end != -1:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            log_error(f"⚠️ Failed to parse analysis response: {e}")
            return self._fallback_analysis(response)
    
    def _fallback_analysis(self, user_input: str) -> Dict[str, Any]:
        """Provide basic analysis when LLM analysis fails."""
        return {
            "content_type": "action",
            "intent": "User interaction",
            "entities": {
                "characters": [],
                "locations": [],
                "items": [],
                "emotions": []
            },
            "content_flags": {
                "nsfw": False,
                "violence": False,
                "mature_themes": False,
                "emotional_intensity": "medium"
            },
            "required_canon": [],
            "memory_triggers": [],
            "response_style": "narrative",
            "token_priority": "medium"
        }
    
    async def optimize_canon_selection(self, analysis: Dict[str, Any], story_data: Dict[str, Any]) -> List[str]:
        """
        Select relevant canon snippets based on content analysis.
        """
        canon_dir = os.path.join(story_data["path"], "canon")
        if not os.path.exists(canon_dir):
            return []
        
        # Get all available canon files (JSON and TXT)
        json_files = [f[:-5] for f in os.listdir(canon_dir) if f.endswith(".json")]
        txt_files = [f[:-4] for f in os.listdir(canon_dir) if f.endswith(".txt")]
        canon_files = json_files + txt_files
        
        # If analysis suggests specific canon files, use those
        required_canon = analysis.get("required_canon", [])
        if required_canon:
            # Filter to only existing files
            selected_canon = [c for c in required_canon if c in canon_files]
            if selected_canon:
                return selected_canon
        
        # Otherwise, use entity-based selection
        entities = analysis.get("entities", {})
        relevant_canon = []
        
        # Check for character-specific canon
        for character in entities.get("characters", []):
            char_canon = f"character_{character.lower().replace(' ', '_')}"
            if char_canon in canon_files:
                relevant_canon.append(char_canon)
        
        # Check for location-specific canon
        for location in entities.get("locations", []):
            loc_canon = f"location_{location.lower().replace(' ', '_')}"
            if loc_canon in canon_files:
                relevant_canon.append(loc_canon)
        
        # Add general canon based on content type
        content_type = analysis.get("content_type", "action")
        if content_type == "dialogue":
            if "dialogue_rules" in canon_files:
                relevant_canon.append("dialogue_rules")
        elif content_type == "action":
            if "world_rules" in canon_files:
                relevant_canon.append("world_rules")
        
        # Limit to prevent token overflow
        return relevant_canon[:3]
    
    async def optimize_memory_context(self, analysis: Dict[str, Any], memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize memory context based on analysis to reduce tokens.
        """
        optimized_memory = {
            "characters": {},
            "world_state": {},
            "flags": [],
            "recent_events": []
        }
        
        # Only include relevant characters
        mentioned_characters = analysis.get("entities", {}).get("characters", [])
        if mentioned_characters and memory.get("characters"):
            for char_name in mentioned_characters:
                # Find character by name (case-insensitive)
                for mem_char, char_data in memory["characters"].items():
                    if char_name.lower() in mem_char.lower():
                        optimized_memory["characters"][mem_char] = char_data
                        break
        elif memory.get("characters"):
            # Include all characters if none specifically mentioned (but limit)
            char_items = list(memory["characters"].items())
            optimized_memory["characters"] = dict(char_items[:3])
        
        # Include relevant world state
        if memory.get("world_state"):
            # For now, include all world state (could be optimized further)
            optimized_memory["world_state"] = memory["world_state"]
        
        # Include relevant flags
        if memory.get("flags"):
            memory_triggers = analysis.get("memory_triggers", [])
            if memory_triggers:
                optimized_memory["flags"] = [
                    flag for flag in memory["flags"]
                    if flag.get("name") in memory_triggers
                ]
            else:
                # Include recent flags
                optimized_memory["flags"] = memory["flags"][-5:]
        
        # Include recent events (always relevant for continuity)
        if memory.get("recent_events"):
            optimized_memory["recent_events"] = memory["recent_events"][-3:]
        
        return optimized_memory
    
    async def generate_content_flags(self, analysis: Dict[str, Any], response: str) -> List[Dict[str, Any]]:
        """
        Generate memory flags based on content analysis and LLM response.
        """
        flags = []
        
        # Add content type flag
        content_type = analysis.get("content_type", "action")
        flags.append({
            "name": f"content_type_{content_type}",
            "value": True,
            "timestamp": datetime.now(UTC).isoformat()
        })
        
        # Add entity flags
        entities = analysis.get("entities", {})
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                if entity:  # Skip empty entities
                    flags.append({
                        "name": f"{entity_type}_{entity.lower().replace(' ', '_')}",
                        "value": True,
                        "timestamp": datetime.now(UTC).isoformat()
                    })
        
        # Add content flags
        content_flags = analysis.get("content_flags", {})
        for flag_name, flag_value in content_flags.items():
            if flag_value and flag_name != "emotional_intensity":
                flags.append({
                    "name": f"content_{flag_name}",
                    "value": flag_value,
                    "timestamp": datetime.now(UTC).isoformat()
                })
        
        # Add emotional intensity flag
        emotional_intensity = content_flags.get("emotional_intensity", "medium")
        flags.append({
            "name": "emotional_intensity",
            "value": emotional_intensity,
            "timestamp": datetime.now(UTC).isoformat()
        })
        
        return flags
    
    def get_routing_recommendation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend model routing based on content analysis.
        """
        content_flags = analysis.get("content_flags", {})
        token_priority = analysis.get("token_priority", "medium")
        
        # Default routing
        recommendation = {
            "adapter": "mock",  # Default to mock for safety
            "max_tokens": 1024,
            "temperature": 0.7,
            "content_filter": False
        }
        
        # Adjust based on content flags
        if content_flags.get("nsfw") or content_flags.get("mature_themes"):
            recommendation["content_filter"] = True
            recommendation["adapter"] = "ollama"  # Use local model for sensitive content
        
        # Adjust token limits based on priority
        if token_priority == "high":
            recommendation["max_tokens"] = 2048
        elif token_priority == "low":
            recommendation["max_tokens"] = 512
        
        # Adjust temperature based on content type
        content_type = analysis.get("content_type", "action")
        if content_type == "dialogue":
            recommendation["temperature"] = 0.8  # More creative for dialogue
        elif content_type == "description":
            recommendation["temperature"] = 0.6  # More focused for descriptions
        
        return recommendation

# For testing purposes
if __name__ == "__main__":
    # Initialize test
    logging.basicConfig(level=logging.INFO)
    from model_adapter import ModelManager
    
    model_manager = ModelManager()
    content_analyzer = ContentAnalyzer(model_manager)
    
    # Test the system
    test_content = "Lyra draws her sword and attacks the dragon"
    print(f"Analyzing: {test_content}")
    
    # Analyze content
    result = content_analyzer.analyze_content(test_content)
    print(f"Content analysis result: {result}")
    
    # Test content type detection
    content_type = content_analyzer.detect_content_type(test_content)
    print(f"Content type: {content_type}")
    
    # Test model recommendation
    model = content_analyzer.get_best_analysis_model(content_type)
    print(f"Recommended model: {model}")
    
    print("Content analysis system test complete!")

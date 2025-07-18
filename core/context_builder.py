import os
import json
import random
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent.parent / "utilities"))
from logging_system import log_system_event, log_info, log_warning, log_error

from .memory_manager import load_current_memory
from .content_analyzer import ContentAnalyzer
from .character_style_manager import CharacterStyleManager
from .token_manager import TokenManager

def load_canon_snippets(storypack_path, refs=None, limit=5):
    canon_dir = os.path.join(storypack_path, "canon")
    snippets = []

    if not os.path.exists(canon_dir):
        return snippets

    if refs:
        for ref in refs:
            # Try JSON first, then fallback to TXT for backward compatibility
            json_path = os.path.join(canon_dir, f"{ref}.json")
            txt_path = os.path.join(canon_dir, f"{ref}.txt")
            
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert JSON to readable text format
                    snippets.append(json_to_readable_text(data))
            elif os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    snippets.append(f.read().strip())
    else:
        # Load random canon snippets if no refs provided
        canon_files = [f for f in os.listdir(canon_dir) if f.endswith((".json", ".txt"))]
        if canon_files:
            random.shuffle(canon_files)
            for filename in canon_files[:limit]:
                file_path = os.path.join(canon_dir, filename)
                if filename.endswith(".json"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        snippets.append(json_to_readable_text(data))
                else:
                    with open(file_path, "r", encoding="utf-8") as f:
                        snippets.append(f.read().strip())

    return snippets

def json_to_readable_text(data, indent=0):
    """Convert JSON data to readable text format for context injection."""
    lines = []
    prefix = "  " * indent
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key.replace('_', ' ').title()}:")
                lines.append(json_to_readable_text(value, indent + 1))
            else:
                lines.append(f"{prefix}{key.replace('_', ' ').title()}: {value}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}- {json_to_readable_text(item, indent + 1)}")
            else:
                lines.append(f"{prefix}- {item}")
    else:
        return str(data)
    
    return "\n".join(lines)

def build_context(user_input, story_data):
    """
    Build context with basic analysis (synchronous version).
    For advanced analysis, use build_context_with_analysis.
    """
    story_id = story_data["id"]
    story_path = story_data["path"]

    memory = load_current_memory(story_id)
    canon_chunks = load_canon_snippets(story_path)

    # Build memory summary for context
    memory_summary = []
    if memory.get("characters"):
        memory_summary.append("=== CHARACTERS ===")
        for char_name, char_data in memory["characters"].items():
            memory_summary.append(f"{char_name}: {char_data.get('current_state', {})}")
    
    if memory.get("world_state"):
        memory_summary.append("=== WORLD STATE ===")
        for key, value in memory["world_state"].items():
            memory_summary.append(f"{key}: {value}")
    
    if memory.get("flags"):
        memory_summary.append("=== ACTIVE FLAGS ===")
        for flag in memory["flags"]:
            memory_summary.append(f"- {flag['name']}")
    
    if memory.get("recent_events"):
        memory_summary.append("=== RECENT EVENTS ===")
        for event in memory["recent_events"][-5:]:  # Last 5 events
            memory_summary.append(f"- {event['description']}")

    prompt_parts = [
        "You are continuing a fictional interactive narrative.",
        f"Story Title: {story_data['meta'].get('title', 'Untitled')}",
        "",
        "=== CANON ===",
        *canon_chunks,
        "",
        *memory_summary,
        "",
        "=== USER INPUT ===",
        user_input,
        "",
        "Continue the story with rich detail and continuity."
    ]

    prompt = "\n".join(prompt_parts)
    return {
        "prompt": prompt,
        "full_context": prompt,  # For compatibility
        "memory": memory,
        "canon_used": canon_chunks,
        "analysis": None  # No analysis in basic version
    }

async def build_context_with_analysis(user_input, story_data):
    """
    Build optimized context using content analysis.
    This is the new intelligent version that reduces tokens.
    """
    from .content_analyzer import ContentAnalyzer
    from .model_adapter import ModelManager
    
    # Initialize content analyzer
    model_manager = ModelManager()
    content_analyzer = ContentAnalyzer(model_manager)
    
    story_id = story_data["id"]
    story_path = story_data["path"]

    # Step 1: Analyze user input
    story_context = {
        "story_id": story_id,
        "meta": story_data.get("meta", {}),
        "characters": {}
    }
    
    # Load current memory for character context
    memory = load_current_memory(story_id)
    if memory.get("characters"):
        story_context["characters"] = memory["characters"]

    analysis = await content_analyzer.analyze_user_input(user_input, story_context)
    
    # Step 2: Select optimized canon based on analysis
    optimized_canon_refs = await content_analyzer.optimize_canon_selection(analysis, story_data)
    canon_chunks = load_canon_snippets(story_path, refs=optimized_canon_refs)
    
    # Step 3: Optimize memory context
    optimized_memory = await content_analyzer.optimize_memory_context(analysis, memory)
    
    # Step 4: Build optimized memory summary
    memory_summary = []
    if optimized_memory.get("characters"):
        memory_summary.append("=== CHARACTERS ===")
        for char_name, char_data in optimized_memory["characters"].items():
            memory_summary.append(f"{char_name}: {char_data.get('current_state', {})}")
    
    if optimized_memory.get("world_state"):
        memory_summary.append("=== WORLD STATE ===")
        for key, value in optimized_memory["world_state"].items():
            memory_summary.append(f"{key}: {value}")
    
    if optimized_memory.get("flags"):
        memory_summary.append("=== ACTIVE FLAGS ===")
        for flag in optimized_memory["flags"]:
            memory_summary.append(f"- {flag['name']}")
    
    if optimized_memory.get("recent_events"):
        memory_summary.append("=== RECENT EVENTS ===")
        for event in optimized_memory["recent_events"]:
            memory_summary.append(f"- {event['description']}")

    # Step 5: Build optimized prompt
    response_style = analysis.get("response_style", "narrative")
    content_type = analysis.get("content_type", "action")
    
    # Customize prompt based on analysis
    style_instruction = {
        "narrative": "Continue the story with rich detail and continuity.",
        "descriptive": "Provide vivid descriptions of the scene and atmosphere.",
        "action": "Focus on action and movement in your response.",
        "dialogue": "Emphasize character dialogue and interaction."
    }.get(response_style, "Continue the story with rich detail and continuity.")
    
    prompt_parts = [
        "You are continuing a fictional interactive narrative.",
        f"Story Title: {story_data['meta'].get('title', 'Untitled')}",
        f"Content Type: {content_type}",
        "",
        "=== CANON ===",
        *canon_chunks,
        "",
        *memory_summary,
        "",
        "=== USER INPUT ===",
        user_input,
        "",
        style_instruction
    ]

    prompt = "\n".join(prompt_parts)
    
    return {
        "prompt": prompt,
        "full_context": prompt,
        "memory": memory,  # Return full memory for logging
        "optimized_memory": optimized_memory,
        "canon_used": canon_chunks,
        "analysis": analysis,
        "routing": content_analyzer.get_routing_recommendation(analysis)
    }

async def build_context_with_dynamic_models(user_input: str, story_data: Dict[str, Any], 
                                          model_manager) -> Dict[str, Any]:
    """
    Build context with dynamic model selection and optimization.
    """
    story_id = story_data["id"]
    story_path = story_data["path"]
    
    # Initialize managers
    content_analyzer = ContentAnalyzer(model_manager)
    character_manager = CharacterStyleManager(model_manager)
    token_manager = TokenManager(model_manager)
    
    # Load character styles
    character_manager.load_character_styles(story_path)
    
    # Analyze user input for optimal model selection
    try:
        analysis = await content_analyzer.analyze_user_input(user_input, {
            "story_id": story_id,
            "meta": story_data.get("meta", {}),
            "characters": story_data.get("characters", {})
        })
        
        recommended_model = analysis.get("routing_recommendation", "mock")
        content_type = analysis.get("content_type", "general")
        
        log_system_event("context_building", 
                        f"Recommended model: {recommended_model} for {content_type}")
        
    except Exception as e:
        log_error(f"Content analysis failed, using fallback: {e}")
        analysis = {"routing_recommendation": "mock", "content_type": "general"}
        recommended_model = "mock"
        content_type = "general"
    
    # Load memory and canon
    memory = load_current_memory(story_id)
    canon_chunks = load_canon_snippets(story_path)
    
    # Determine active character if any
    active_character = None
    if analysis.get("entities", {}).get("characters"):
        active_character = analysis["entities"]["characters"][0]
    
    # Select model based on character and content
    if active_character:
        selected_model = character_manager.select_character_model(
            active_character, content_type)
        if selected_model != recommended_model:
            log_info(f"Character-specific model override: {selected_model} for {active_character}")
            recommended_model = selected_model
    
    # Build context parts
    context_parts = {
        "system": _build_system_context(story_data),
        "memory": _build_memory_context(memory),
        "canon": _build_canon_context(canon_chunks),
        "user_input": user_input
    }
    
    # Add character style context if applicable
    if active_character:
        character_context = character_manager.build_character_context(
            active_character, recommended_model)
        if character_context:
            context_parts["character_style"] = character_context
    
    # Estimate token usage and trim if necessary
    estimated_tokens = sum(
        token_manager.estimate_tokens(part, recommended_model)
        for part in context_parts.values()
    )
    
    # Check if we need to trim for token limits
    model_config = model_manager.get_adapter_info(recommended_model)
    max_tokens = model_config.get("max_tokens", 4096)
    target_tokens = int(max_tokens * 0.6)  # Leave room for response
    
    if estimated_tokens > target_tokens:
        log_warning(f"Context too long ({estimated_tokens} tokens), trimming to {target_tokens}")
        context_parts = token_manager.trim_context_intelligently(
            context_parts, target_tokens, recommended_model)
    
    # Build final context
    final_context = _assemble_context(context_parts)
    
    return {
        "context": final_context,
        "recommended_model": recommended_model,
        "content_analysis": analysis,
        "active_character": active_character,
        "token_estimate": token_manager.estimate_tokens(final_context, recommended_model)
    }

def _build_system_context(story_data: Dict[str, Any]) -> str:
    """Build system context section."""
    return f"""You are continuing a fictional interactive narrative.
Story Title: {story_data['meta'].get('title', 'Untitled')}
Description: {story_data['meta'].get('description', 'No description')}"""

def _build_memory_context(memory: Dict[str, Any]) -> str:
    """Build memory context section."""
    parts = []
    
    if memory.get("characters"):
        parts.append("=== CHARACTERS ===")
        for char_name, char_data in memory["characters"].items():
            parts.append(f"{char_name}: {char_data.get('current_state', {})}")
    
    if memory.get("world_state"):
        parts.append("=== WORLD STATE ===")
        for key, value in memory["world_state"].items():
            parts.append(f"{key}: {value}")
    
    if memory.get("flags"):
        parts.append("=== ACTIVE FLAGS ===")
        for flag in memory["flags"]:
            parts.append(f"- {flag['name']}")
    
    if memory.get("recent_events"):
        parts.append("=== RECENT EVENTS ===")
        for event in memory["recent_events"][-5:]:
            parts.append(f"- {event['description']}")
    
    return "\n".join(parts)

def _build_canon_context(canon_chunks: List[str]) -> str:
    """Build canon context section."""
    if not canon_chunks:
        return ""
    
    parts = ["=== CANON ==="]
    parts.extend(canon_chunks)
    return "\n".join(parts)

def _assemble_context(context_parts: Dict[str, str]) -> str:
    """Assemble final context from parts."""
    sections = []
    
    # Order matters for context flow
    section_order = ["system", "memory", "canon", "character_style", "user_input"]
    
    for section in section_order:
        if section in context_parts and context_parts[section]:
            if section == "user_input":
                sections.append(f"USER INPUT: {context_parts[section]}")
            else:
                sections.append(context_parts[section])
    
    sections.append("\nContinue the story naturally based on the user's input, maintaining consistency with the established world and characters.")
    
    return "\n\n".join(sections)
import os
import json
import random
from .memory_manager import load_current_memory
from .content_analyzer import content_analyzer

def load_canon_snippets(storypack_path, refs=None, limit=5):
    canon_dir = os.path.join(storypack_path, "canon")
    snippets = []

    if not os.path.exists(canon_dir):
        return snippets

    if refs:
        for ref in refs:
            file_path = os.path.join(canon_dir, f"{ref}.txt")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    snippets.append(f.read().strip())
    else:
        # Load random canon snippets if no refs provided
        canon_files = [f for f in os.listdir(canon_dir) if f.endswith(".txt")]
        if canon_files:
            random.shuffle(canon_files)
            for filename in canon_files[:limit]:
                with open(os.path.join(canon_dir, filename), "r", encoding="utf-8") as f:
                    snippets.append(f.read().strip())

    return snippets

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
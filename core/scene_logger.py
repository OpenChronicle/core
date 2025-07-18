import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from .database import get_connection, execute_query, execute_update, init_database

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent.parent / "utilities"))
from logging_system import log_system_event, log_info, log_warning, log_error

def generate_scene_id():
    import time
    return str(int(time.time() * 1000000))  # Use microseconds for uniqueness

def save_scene(story_id, user_input, model_output, memory_snapshot=None, flags=None, context_refs=None, 
               analysis_data=None, scene_label=None, token_manager=None, model_name=None, 
               structured_tags=None):
    """
    Save a scene to the database with enhanced structured tags and token tracking.
    
    Args:
        story_id: Story identifier
        user_input: User's input text
        model_output: Model's response text
        memory_snapshot: Memory state at scene time
        flags: Memory flags
        context_refs: Canon references used
        analysis_data: Content analysis results
        scene_label: Scene label for organization
        token_manager: Token manager instance for token tracking
        model_name: Model used for generation
        structured_tags: Additional structured metadata
    
    Returns:
        scene_id: Generated scene identifier
    """
    init_database(story_id)
    
    scene_id = generate_scene_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Prepare analysis data for storage
    analysis_json = json.dumps(analysis_data) if analysis_data else None
    
    # Build structured tags
    if structured_tags is None:
        structured_tags = {}
    
    # Add token information if token_manager is provided
    if token_manager and model_name:
        try:
            input_tokens = token_manager.estimate_tokens(user_input, model_name)
            output_tokens = token_manager.estimate_tokens(model_output, model_name)
            total_tokens = input_tokens + output_tokens
            
            # Check if this is a long turn
            is_long_turn = token_manager.check_token_usage(user_input + model_output, model_name)
            
            structured_tags.update({
                "token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "model_used": model_name,
                    "is_long_turn": is_long_turn,
                    "timestamp": timestamp
                }
            })
            
            # Log token usage
            log_info(f"Scene {scene_id}: {total_tokens} tokens ({model_name})")
            if is_long_turn:
                log_warning(f"Long turn detected in scene {scene_id}: {total_tokens} tokens")
                
        except Exception as e:
            log_error(f"Error calculating token usage for scene {scene_id}: {e}")
    
    # Extract mood and scene type from analysis or memory
    if analysis_data:
        mood = analysis_data.get("detected_mood", "neutral")
        scene_type = analysis_data.get("scene_type", "dialogue")
        content_type = analysis_data.get("content_type", "general")
        
        structured_tags.update({
            "mood": mood,
            "scene_type": scene_type,
            "content_type": content_type
        })
    
    # Extract character moods from memory snapshot
    if memory_snapshot and "characters" in memory_snapshot:
        character_moods = {}
        for char_name, char_data in memory_snapshot["characters"].items():
            mood_state = char_data.get("mood_state", {})
            if mood_state:
                character_moods[char_name] = {
                    "mood": mood_state.get("current_mood", "neutral"),
                    "stability": mood_state.get("mood_stability", 1.0)
                }
        
        if character_moods:
            structured_tags["character_moods"] = character_moods
    
    # Add scene metadata
    structured_tags.update({
        "scene_id": scene_id,
        "timestamp": timestamp,
        "input_length": len(user_input),
        "output_length": len(model_output),
        "memory_flags_count": len(flags or []),
        "canon_refs_count": len(context_refs or [])
    })
    
    execute_update(story_id, '''
        INSERT OR REPLACE INTO scenes 
        (scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs, analysis, scene_label, structured_tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        scene_id,
        timestamp,
        user_input,
        model_output,
        json.dumps(memory_snapshot or {}),
        json.dumps(flags or []),
        json.dumps(context_refs or []),
        analysis_json,
        scene_label,
        json.dumps(structured_tags)
    ))
    
    log_info(f"Scene {scene_id} saved with structured tags: {list(structured_tags.keys())}")
    return scene_id

def load_scene(story_id, scene_id):
    """Load a scene from the database."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs, scene_label, structured_tags
        FROM scenes WHERE scene_id = ?
    ''', (scene_id,))
    
    if not rows:
        raise FileNotFoundError(f"No scene found: {scene_id}")
    
    row = rows[0]
    return {
        "scene_id": row["scene_id"],
        "timestamp": row["timestamp"],
        "input": row["input"],
        "output": row["output"],
        "memory": json.loads(row["memory_snapshot"] or "{}"),
        "flags": json.loads(row["flags"] or "[]"),
        "canon_refs": json.loads(row["canon_refs"] or "[]"),
        "scene_label": row["scene_label"],
        "structured_tags": json.loads(row["structured_tags"] or "{}")
    }

def get_scenes_with_long_turns(story_id: str) -> List[Dict[str, Any]]:
    """
    Get all scenes that were flagged as long turns.
    
    Args:
        story_id: Story identifier
    
    Returns:
        List of scene data with long turn information
    """
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, input, output, structured_tags, scene_label
        FROM scenes WHERE structured_tags LIKE '%"long_turn": true%'
        ORDER BY timestamp DESC
    ''')
    
    long_turn_scenes = []
    for row in rows:
        try:
            structured_tags = json.loads(row["structured_tags"] or "{}")
            
            # Check both locations for long_turn flag
            is_long_turn = (structured_tags.get("long_turn", False) or 
                           structured_tags.get("token_usage", {}).get("is_long_turn", False))
            
            if is_long_turn:
                long_turn_scenes.append({
                    "scene_id": row["scene_id"],
                    "timestamp": row["timestamp"],
                    "scene_label": row["scene_label"],
                    "input_preview": row["input"][:100] + "..." if len(row["input"]) > 100 else row["input"],
                    "output_preview": row["output"][:100] + "..." if len(row["output"]) > 100 else row["output"],
                    "structured_tags": structured_tags
                })
        except json.JSONDecodeError:
            continue
    
    return long_turn_scenes

def get_scenes_by_mood(story_id: str, mood: str) -> List[Dict[str, Any]]:
    """
    Get scenes filtered by mood.
    
    Args:
        story_id: Story identifier
        mood: Mood to filter by
    
    Returns:
        List of scenes with the specified mood
    """
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, input, output, structured_tags, scene_label
        FROM scenes WHERE structured_tags LIKE ?
        ORDER BY timestamp ASC
    ''', (f'%"mood": "{mood}"%',))
    
    mood_scenes = []
    for row in rows:
        try:
            structured_tags = json.loads(row["structured_tags"] or "{}")
            if structured_tags.get("mood") == mood:
                mood_scenes.append({
                    "scene_id": row["scene_id"],
                    "timestamp": row["timestamp"],
                    "scene_label": row["scene_label"],
                    "input": row["input"],
                    "output": row["output"],
                    "structured_tags": structured_tags
                })
        except json.JSONDecodeError:
            continue
    
    return mood_scenes

def get_scenes_by_type(story_id: str, scene_type: str) -> List[Dict[str, Any]]:
    """
    Get scenes filtered by scene type.
    
    Args:
        story_id: Story identifier
        scene_type: Scene type to filter by (dialogue, action, description, etc.)
    
    Returns:
        List of scenes with the specified type
    """
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, input, output, structured_tags, scene_label
        FROM scenes WHERE structured_tags LIKE ?
        ORDER BY timestamp ASC
    ''', (f'%"scene_type": "{scene_type}"%',))
    
    type_scenes = []
    for row in rows:
        try:
            structured_tags = json.loads(row["structured_tags"] or "{}")
            if structured_tags.get("scene_type") == scene_type:
                type_scenes.append({
                    "scene_id": row["scene_id"],
                    "timestamp": row["timestamp"],
                    "scene_label": row["scene_label"],
                    "input": row["input"],
                    "output": row["output"],
                    "structured_tags": structured_tags
                })
        except json.JSONDecodeError:
            continue
    
    return type_scenes

def get_token_usage_stats(story_id: str) -> Dict[str, Any]:
    """
    Get token usage statistics for a story.
    
    Args:
        story_id: Story identifier
    
    Returns:
        Token usage statistics
    """
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT structured_tags FROM scenes WHERE structured_tags IS NOT NULL
    ''')
    
    total_tokens = 0
    total_input_tokens = 0
    total_output_tokens = 0
    long_turn_count = 0
    model_usage = {}
    scene_count = 0
    
    for row in rows:
        try:
            structured_tags = json.loads(row["structured_tags"] or "{}")
            token_usage = structured_tags.get("token_usage", {})
            
            if token_usage:
                scene_count += 1
                input_tokens = token_usage.get("input_tokens", 0)
                output_tokens = token_usage.get("output_tokens", 0)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                total_tokens += input_tokens + output_tokens
                
                if token_usage.get("is_long_turn", False):
                    long_turn_count += 1
                
                model_used = token_usage.get("model_used", "unknown")
                if model_used not in model_usage:
                    model_usage[model_used] = {"scenes": 0, "tokens": 0}
                model_usage[model_used]["scenes"] += 1
                model_usage[model_used]["tokens"] += input_tokens + output_tokens
                
        except json.JSONDecodeError:
            continue
    
    return {
        "total_tokens": total_tokens,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "average_tokens_per_scene": total_tokens / scene_count if scene_count > 0 else 0,
        "long_turn_count": long_turn_count,
        "long_turn_percentage": (long_turn_count / scene_count * 100) if scene_count > 0 else 0,
        "model_usage": model_usage,
        "scene_count": scene_count
    }

def get_character_mood_timeline(story_id: str, character_name: str) -> List[Dict[str, Any]]:
    """
    Get character mood changes over time.
    
    Args:
        story_id: Story identifier
        character_name: Character name to track
    
    Returns:
        List of mood changes with timestamps
    """
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, structured_tags, scene_label
        FROM scenes WHERE structured_tags LIKE ?
        ORDER BY timestamp ASC
    ''', (f'%"{character_name}"%',))
    
    mood_timeline = []
    for row in rows:
        try:
            structured_tags = json.loads(row["structured_tags"] or "{}")
            character_moods = structured_tags.get("character_moods", {})
            
            if character_name in character_moods:
                char_mood = character_moods[character_name]
                mood_timeline.append({
                    "scene_id": row["scene_id"],
                    "timestamp": row["timestamp"],
                    "scene_label": row["scene_label"],
                    "mood": char_mood.get("mood", "neutral"),
                    "stability": char_mood.get("stability", 1.0)
                })
        except json.JSONDecodeError:
            continue
    
    return mood_timeline

def list_scenes(story_id):
    """List all scene IDs for a story."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, scene_label, structured_tags FROM scenes ORDER BY timestamp ASC
    ''')
    
    scenes = []
    for row in rows:
        scene_data = {
            "scene_id": row["scene_id"],
            "timestamp": row["timestamp"],
            "scene_label": row["scene_label"]
        }
        
        # Add structured tag summary
        try:
            structured_tags = json.loads(row["structured_tags"] or "{}")
            scene_data["mood"] = structured_tags.get("mood", "neutral")
            scene_data["scene_type"] = structured_tags.get("scene_type", "dialogue")
            
            token_usage = structured_tags.get("token_usage", {})
            if token_usage:
                scene_data["total_tokens"] = token_usage.get("total_tokens", 0)
                scene_data["is_long_turn"] = token_usage.get("is_long_turn", False)
                scene_data["model_used"] = token_usage.get("model_used", "unknown")
        except json.JSONDecodeError:
            scene_data["mood"] = "neutral"
            scene_data["scene_type"] = "dialogue"
        
        scenes.append(scene_data)
    
    return scenes

def update_scene_label(story_id, scene_id, scene_label):
    """Update the label for a specific scene."""
    init_database(story_id)
    
    rowcount = execute_update(story_id, '''
        UPDATE scenes SET scene_label = ? WHERE scene_id = ?
    ''', (scene_label, scene_id))
    
    return rowcount > 0

def get_scenes_by_label(story_id, scene_label):
    """Get all scenes with a specific label."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs, scene_label
        FROM scenes WHERE scene_label = ? ORDER BY timestamp ASC
    ''', (scene_label,))
    
    return [{
        "scene_id": row["scene_id"],
        "timestamp": row["timestamp"],
        "input": row["input"],
        "output": row["output"],
        "memory": json.loads(row["memory_snapshot"] or "{}"),
        "flags": json.loads(row["flags"] or "[]"),
        "canon_refs": json.loads(row["canon_refs"] or "[]"),
        "scene_label": row["scene_label"]
    } for row in rows]

def get_labeled_scenes(story_id):
    """Get all scenes that have labels."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, scene_label, input
        FROM scenes WHERE scene_label IS NOT NULL AND scene_label != ''
        ORDER BY timestamp ASC
    ''')
    
    return [{
        "scene_id": row["scene_id"],
        "timestamp": row["timestamp"],
        "scene_label": row["scene_label"],
        "input": row["input"]
    } for row in rows]

def rollback_to_scene(story_id, scene_id):
    """Returns scene input/output/memory to rebuild current state."""
    scene = load_scene(story_id, scene_id)
    return {
        "scene_id": scene["scene_id"],
        "input": scene["input"],
        "output": scene["output"],
        "memory": scene.get("memory", {}),
        "flags": scene.get("flags", [])
    }

def get_scene_summary_stats(story_id: str) -> Dict[str, Any]:
    """
    Get summary statistics about scenes with structured tags.
    
    Args:
        story_id: The story identifier
    
    Returns:
        Dictionary containing scene statistics
    """
    try:
        from .database import execute_query
        init_database(story_id)
        
        # Get all scenes with structured tags
        rows = execute_query(story_id, '''
            SELECT structured_tags FROM scenes 
            WHERE structured_tags IS NOT NULL 
            ORDER BY created_at
        ''')
        
        stats = {
            "total_scenes": len(rows),
            "scenes_by_location": {},
            "scenes_by_mood": {},
            "scenes_by_action_type": {},
            "scenes_by_significance": {},
            "long_turn_scenes": 0
        }
        
        for row in rows:
            try:
                tags = json.loads(row["structured_tags"])
                
                # Count by location
                location = tags.get("location", "unknown")
                stats["scenes_by_location"][location] = stats["scenes_by_location"].get(location, 0) + 1
                
                # Count by mood
                mood = tags.get("mood", "neutral")
                stats["scenes_by_mood"][mood] = stats["scenes_by_mood"].get(mood, 0) + 1
                
                # Count by action type
                action_type = tags.get("action_type", "general")
                stats["scenes_by_action_type"][action_type] = stats["scenes_by_action_type"].get(action_type, 0) + 1
                
                # Count by significance
                significance = tags.get("significance", "medium")
                stats["scenes_by_significance"][significance] = stats["scenes_by_significance"].get(significance, 0) + 1
                
                # Count long turn scenes
                if tags.get("long_turn", False):
                    stats["long_turn_scenes"] += 1
                    
            except (json.JSONDecodeError, KeyError) as e:
                log_warning(f"Error parsing structured tags: {e}")
                continue
        
        return stats
        
    except Exception as e:
        log_error(f"Error getting scene summary stats: {e}")
        return {
            "total_scenes": 0,
            "scenes_by_location": {},
            "scenes_by_mood": {},
            "scenes_by_action_type": {},
            "scenes_by_significance": {},
            "long_turn_scenes": 0
        }
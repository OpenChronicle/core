import os
import json
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from .database import get_connection, execute_query, execute_update, init_database

# Add utilities to path for logging system
sys.path.append(str(Path(__file__).parent.parent / "utilities"))
from logging_system import log_system_event, log_info, log_warning, log_error

def load_current_memory(story_id):
    """Load the current memory state for a story from database."""
    init_database(story_id)
    
    # Get all current memory entries
    rows = execute_query(story_id, '''
        SELECT type, key, value FROM memory 
        WHERE story_id = ? ORDER BY updated_at DESC
    ''', (story_id,))
    
    memory = {
        "characters": {},
        "world_state": {},
        "flags": [],
        "recent_events": [],
        "metadata": {
            "created": datetime.now(UTC).isoformat(),
            "last_updated": datetime.now(UTC).isoformat()
        }
    }
    
    for row in rows:
        memory_type = row["type"]
        key = row["key"]
        value = json.loads(row["value"])
        
        if memory_type == "characters":
            memory["characters"] = value
        elif memory_type == "world_state":
            memory["world_state"] = value
        elif memory_type == "flags":
            memory["flags"] = value
        elif memory_type == "recent_events":
            memory["recent_events"] = value
        elif memory_type == "metadata":
            memory["metadata"] = value
    
    return memory

def save_current_memory(story_id, memory_data):
    """Save the current memory state to database."""
    init_database(story_id)
    
    # Update metadata
    memory_data["metadata"]["last_updated"] = datetime.now(UTC).isoformat()
    
    timestamp = datetime.now(UTC).isoformat()
    
    # Save each memory type
    for memory_type in ["characters", "world_state", "flags", "recent_events", "metadata"]:
        if memory_type in memory_data:
            execute_update(story_id, '''
                INSERT OR REPLACE INTO memory 
                (story_id, type, key, value, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                story_id,
                memory_type,
                "current",
                json.dumps(memory_data[memory_type]),
                timestamp
            ))

def archive_memory_snapshot(story_id, scene_id, memory_data):
    """Archive a memory snapshot linked to a scene."""
    init_database(story_id)
    
    execute_update(story_id, '''
        INSERT INTO memory_history (scene_id, timestamp, memory_data)
        VALUES (?, ?, ?)
    ''', (
        scene_id,
        datetime.now(UTC).isoformat(),
        json.dumps(memory_data)
    ))
    
    # Keep only last 50 snapshots to prevent bloat
    execute_update(story_id, '''
        DELETE FROM memory_history 
        WHERE id NOT IN (
            SELECT id FROM memory_history 
            ORDER BY created_at DESC 
            LIMIT 50
        )
    ''')

def update_character_memory(story_id, character_name, updates):
    """Update memory for a specific character."""
    memory = load_current_memory(story_id)
    
    if character_name not in memory["characters"]:
        memory["characters"][character_name] = {
            "traits": {},
            "relationships": {},
            "history": [],
            "current_state": {},
            "voice_profile": {
                "speaking_style": "default",
                "tone": "neutral",
                "vocabulary_level": "standard",
                "emotional_state": "stable"
            },
            "mood_state": {
                "current_mood": "neutral",
                "mood_history": [],
                "emotional_triggers": [],
                "mood_stability": 1.0
            }
        }
    
    character = memory["characters"][character_name]
    
    # Ensure enhanced fields exist for existing characters
    if "voice_profile" not in character:
        character["voice_profile"] = {
            "speaking_style": "default",
            "tone": "neutral",
            "vocabulary_level": "standard",
            "emotional_state": "stable"
        }
    
    if "mood_state" not in character:
        character["mood_state"] = {
            "current_mood": "neutral",
            "mood_history": [],
            "emotional_triggers": [],
            "mood_stability": 1.0
        }
    
    # Apply updates
    for key, value in updates.items():
        if key == "traits":
            character["traits"].update(value)
        elif key == "relationships":
            character["relationships"].update(value)
        elif key == "history":
            if isinstance(value, list):
                character["history"].extend(value)
            else:
                character["history"].append(value)
        elif key == "current_state":
            character["current_state"].update(value)
        elif key == "voice_profile":
            character["voice_profile"].update(value)
        elif key == "mood_state":
            character["mood_state"].update(value)
            # Track mood changes in history
            if "current_mood" in value:
                character["mood_state"]["mood_history"].append({
                    "mood": value["current_mood"],
                    "timestamp": datetime.now(UTC).isoformat(),
                    "scene_context": value.get("scene_context", "")
                })
                # Keep only last 20 mood changes
                character["mood_state"]["mood_history"] = character["mood_state"]["mood_history"][-20:]
    
    save_current_memory(story_id, memory)
    return memory

def get_character_memory_snapshot(story_id: str, character_name: str, format_for_prompt: bool = True) -> Dict[str, Any]:
    """
    Get formatted character memory snapshot for prompt injection.
    
    Args:
        story_id: The story identifier
        character_name: Name of the character
        format_for_prompt: Whether to format for LLM prompt context
    
    Returns:
        Formatted character memory snapshot
    """
    try:
        memory = load_current_memory(story_id)
        character = memory["characters"].get(character_name, {})
        
        if not character:
            log_warning(f"Character '{character_name}' not found in memory")
            return {}
        
        snapshot = {
            "character_name": character_name,
            "traits": character.get("traits", {}),
            "relationships": character.get("relationships", {}),
            "current_state": character.get("current_state", {}),
            "voice_profile": character.get("voice_profile", {}),
            "mood_state": character.get("mood_state", {}),
            "recent_history": character.get("history", [])[-5:],  # Last 5 history items
            "snapshot_timestamp": datetime.now(UTC).isoformat()
        }
        
        if format_for_prompt:
            return format_character_snapshot_for_prompt(snapshot)
        
        return snapshot
        
    except Exception as e:
        log_error(f"Error getting character memory snapshot for '{character_name}': {e}")
        return {}

def format_character_snapshot_for_prompt(snapshot: Dict[str, Any]) -> str:
    """
    Format character snapshot for LLM prompt injection.
    
    Args:
        snapshot: Character memory snapshot
    
    Returns:
        Formatted string for prompt context
    """
    char_name = snapshot.get("character_name", "Unknown")
    lines = [f"=== {char_name.upper()} CHARACTER MEMORY ==="]
    
    # Voice Profile
    voice = snapshot.get("voice_profile", {})
    if voice:
        lines.append(f"Voice: {voice.get('speaking_style', 'default')} style, {voice.get('tone', 'neutral')} tone")
        lines.append(f"Vocabulary: {voice.get('vocabulary_level', 'standard')}")
        lines.append(f"Emotional State: {voice.get('emotional_state', 'stable')}")
    
    # Current Mood
    mood = snapshot.get("mood_state", {})
    if mood:
        lines.append(f"Current Mood: {mood.get('current_mood', 'neutral')}")
        mood_stability = mood.get("mood_stability", 1.0)
        lines.append(f"Mood Stability: {mood_stability:.1f}/1.0")
        
        # Recent mood changes
        mood_history = mood.get("mood_history", [])
        if mood_history:
            lines.append("Recent Mood Changes:")
            for mood_entry in mood_history[-3:]:  # Last 3 mood changes
                lines.append(f"  - {mood_entry['mood']} ({mood_entry['timestamp'][:10]})")
    
    # Current State
    current_state = snapshot.get("current_state", {})
    if current_state:
        lines.append("Current State:")
        for key, value in current_state.items():
            lines.append(f"  {key}: {value}")
    
    # Key Traits
    traits = snapshot.get("traits", {})
    if traits:
        lines.append("Key Traits:")
        for trait, value in traits.items():
            lines.append(f"  {trait}: {value}")
    
    # Important Relationships
    relationships = snapshot.get("relationships", {})
    if relationships:
        lines.append("Relationships:")
        for person, relationship in relationships.items():
            lines.append(f"  {person}: {relationship}")
    
    # Recent History
    history = snapshot.get("recent_history", [])
    if history:
        lines.append("Recent History:")
        for item in history:
            if isinstance(item, dict):
                lines.append(f"  - {item.get('description', str(item))}")
            else:
                lines.append(f"  - {item}")
    
    return "\n".join(lines)

def refresh_memory_after_rollback(story_id: str, target_scene_id: str) -> Dict[str, Any]:
    """
    Refresh memory state after rollback operation.
    
    Args:
        story_id: The story identifier
        target_scene_id: Scene ID to rollback to
    
    Returns:
        Updated memory state
    """
    try:
        log_info(f"Refreshing memory after rollback to scene: {target_scene_id}")
        
        # Restore memory from snapshot
        memory = restore_memory_from_snapshot(story_id, target_scene_id)
        
        # Update metadata to reflect rollback
        memory["metadata"]["last_rollback"] = {
            "target_scene": target_scene_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": "rollback_operation"
        }
        
        # Reset any temporary states that shouldn't persist across rollbacks
        for char_name in memory.get("characters", {}):
            character = memory["characters"][char_name]
            
            # Reset mood stability to indicate recent change
            if "mood_state" in character:
                character["mood_state"]["mood_stability"] = max(0.7, 
                    character["mood_state"].get("mood_stability", 1.0) - 0.1)
                
                # Add rollback event to mood history
                character["mood_state"]["mood_history"].append({
                    "mood": character["mood_state"].get("current_mood", "neutral"),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "scene_context": f"rollback_to_{target_scene_id}"
                })
        
        # Add rollback event to recent events
        if "recent_events" not in memory:
            memory["recent_events"] = []
        
        memory["recent_events"].append({
            "description": f"Story rolled back to scene: {target_scene_id}",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "event_type": "rollback",
                "target_scene": target_scene_id,
                "affected_characters": list(memory.get("characters", {}).keys())
            }
        })
        
        # Save refreshed memory
        save_current_memory(story_id, memory)
        
        log_info(f"Memory refreshed successfully after rollback to {target_scene_id}")
        return memory
        
    except Exception as e:
        log_error(f"Error refreshing memory after rollback: {e}")
        # Fallback to current memory
        return load_current_memory(story_id)

def get_character_voice_prompt(story_id: str, character_name: str) -> str:
    """
    Get character voice profile formatted for LLM prompt.
    
    Args:
        story_id: The story identifier
        character_name: Name of the character
    
    Returns:
        Voice profile string for prompt context
    """
    try:
        memory = load_current_memory(story_id)
        character = memory["characters"].get(character_name, {})
        voice_profile = character.get("voice_profile", {})
        
        if not voice_profile:
            return f"Character: {character_name} (default voice)"
        
        voice_elements = []
        
        speaking_style = voice_profile.get("speaking_style", "default")
        tone = voice_profile.get("tone", "neutral")
        vocabulary = voice_profile.get("vocabulary_level", "standard")
        emotional_state = voice_profile.get("emotional_state", "stable")
        
        voice_elements.append(f"Speaking Style: {speaking_style}")
        voice_elements.append(f"Tone: {tone}")
        voice_elements.append(f"Vocabulary: {vocabulary}")
        voice_elements.append(f"Emotional State: {emotional_state}")
        
        return f"Character: {character_name}\n" + "\n".join(voice_elements)
        
    except Exception as e:
        log_error(f"Error getting character voice prompt for '{character_name}': {e}")
        return f"Character: {character_name} (voice profile error)"

def update_character_mood(story_id: str, character_name: str, new_mood: str, 
                          scene_context: str = "", emotional_triggers: List[str] = None) -> Dict[str, Any]:
    """
    Update character mood with context and trigger tracking.
    
    Args:
        story_id: The story identifier
        character_name: Name of the character
        new_mood: New mood state
        scene_context: Context of the scene causing mood change
        emotional_triggers: List of triggers that caused the mood change
    
    Returns:
        Updated character memory
    """
    try:
        mood_update = {
            "mood_state": {
                "current_mood": new_mood,
                "scene_context": scene_context
            }
        }
        
        if emotional_triggers:
            mood_update["mood_state"]["emotional_triggers"] = emotional_triggers
        
        memory = update_character_memory(story_id, character_name, mood_update)
        
        log_info(f"Updated mood for {character_name}: {new_mood}")
        return memory
        
    except Exception as e:
        log_error(f"Error updating character mood for '{character_name}': {e}")
        return load_current_memory(story_id)

def update_world_state(story_id, updates):
    """Update world state memory."""
    memory = load_current_memory(story_id)
    memory["world_state"].update(updates)
    save_current_memory(story_id, memory)
    return memory

def add_memory_flag(story_id, flag_name, flag_data=None):
    """Add a memory flag."""
    memory = load_current_memory(story_id)
    
    flag_entry = {
        "name": flag_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": flag_data or {}
    }
    
    memory["flags"].append(flag_entry)
    save_current_memory(story_id, memory)
    return memory

def remove_memory_flag(story_id, flag_name):
    """Remove a memory flag by name."""
    memory = load_current_memory(story_id)
    memory["flags"] = [f for f in memory["flags"] if f["name"] != flag_name]
    save_current_memory(story_id, memory)
    return memory

def has_memory_flag(story_id, flag_name):
    """Check if a memory flag exists."""
    memory = load_current_memory(story_id)
    return any(f["name"] == flag_name for f in memory["flags"])

def add_recent_event(story_id, event_description, event_data=None):
    """Add a recent event to memory."""
    memory = load_current_memory(story_id)
    
    event = {
        "description": event_description,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": event_data or {}
    }
    
    memory["recent_events"].append(event)
    
    # Keep only last 20 events
    memory["recent_events"] = memory["recent_events"][-20:]
    
    save_current_memory(story_id, memory)
    return memory

def get_character_memory(story_id, character_name):
    """Get memory for a specific character."""
    memory = load_current_memory(story_id)
    return memory["characters"].get(character_name, {})

def get_memory_summary(story_id):
    """Get a summary of current memory state."""
    memory = load_current_memory(story_id)
    
    return {
        "character_count": len(memory["characters"]),
        "world_state_keys": list(memory["world_state"].keys()),
        "active_flags": [f["name"] for f in memory["flags"]],
        "recent_events_count": len(memory["recent_events"]),
        "last_updated": memory["metadata"]["last_updated"]
    }

def get_memory_context_for_prompt(story_id: str, primary_characters: List[str] = None, 
                                  include_full_context: bool = True) -> str:
    """
    Get formatted memory context for LLM prompt injection.
    
    Args:
        story_id: The story identifier
        primary_characters: List of primary characters to focus on
        include_full_context: Whether to include full world state and events
    
    Returns:
        Formatted memory context string
    """
    try:
        memory = load_current_memory(story_id)
        context_lines = ["=== MEMORY CONTEXT ==="]
        
        # Character memory snapshots
        characters = memory.get("characters", {})
        if characters:
            if primary_characters:
                # Focus on primary characters first
                context_lines.append("\n=== PRIMARY CHARACTERS ===")
                for char_name in primary_characters:
                    if char_name in characters:
                        snapshot = get_character_memory_snapshot(story_id, char_name, format_for_prompt=False)
                        char_context = format_character_snapshot_for_prompt(snapshot)
                        context_lines.append(char_context)
                
                # Other characters (brief)
                other_chars = [name for name in characters.keys() if name not in primary_characters]
                if other_chars:
                    context_lines.append("\n=== OTHER CHARACTERS ===")
                    for char_name in other_chars:
                        char_data = characters[char_name]
                        mood = char_data.get("mood_state", {}).get("current_mood", "neutral")
                        state_summary = ", ".join(f"{k}: {v}" for k, v in char_data.get("current_state", {}).items())
                        context_lines.append(f"{char_name}: {mood} mood" + (f", {state_summary}" if state_summary else ""))
            else:
                # All characters with full context
                context_lines.append("\n=== ALL CHARACTERS ===")
                for char_name in characters:
                    snapshot = get_character_memory_snapshot(story_id, char_name, format_for_prompt=False)
                    char_context = format_character_snapshot_for_prompt(snapshot)
                    context_lines.append(char_context)
        
        if include_full_context:
            # World state
            world_state = memory.get("world_state", {})
            if world_state:
                context_lines.append("\n=== WORLD STATE ===")
                for key, value in world_state.items():
                    context_lines.append(f"{key}: {value}")
            
            # Active flags
            flags = memory.get("flags", [])
            if flags:
                context_lines.append("\n=== ACTIVE FLAGS ===")
                for flag in flags:
                    flag_name = flag.get("name", "Unknown")
                    flag_data = flag.get("data", {})
                    if flag_data:
                        context_lines.append(f"- {flag_name}: {flag_data}")
                    else:
                        context_lines.append(f"- {flag_name}")
            
            # Recent events
            recent_events = memory.get("recent_events", [])
            if recent_events:
                context_lines.append("\n=== RECENT EVENTS ===")
                for event in recent_events[-5:]:  # Last 5 events
                    event_desc = event.get("description", "Unknown event")
                    timestamp = event.get("timestamp", "")[:10]  # Just date part
                    context_lines.append(f"- {event_desc} ({timestamp})")
        
        return "\n".join(context_lines)
        
    except Exception as e:
        log_error(f"Error getting memory context for prompt: {e}")
        return "=== MEMORY CONTEXT ===\n[Error loading memory context]"

def restore_memory_from_snapshot(story_id, scene_id):
    """Restore memory from a historical snapshot."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT memory_data FROM memory_history 
        WHERE scene_id = ? ORDER BY created_at DESC LIMIT 1
    ''', (scene_id,))
    
    if not rows:
        raise ValueError(f"No memory snapshot found for scene: {scene_id}")
    
    # Restore memory
    memory_data = json.loads(rows[0]["memory_data"])
    save_current_memory(story_id, memory_data)
    
    return memory_data

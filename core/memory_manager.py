import os
import json
from datetime import datetime
from pathlib import Path
from .database import get_connection, execute_query, execute_update, init_database

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
            "created": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
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
    memory_data["metadata"]["last_updated"] = datetime.utcnow().isoformat()
    
    timestamp = datetime.utcnow().isoformat()
    
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
        datetime.utcnow().isoformat(),
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
            "current_state": {}
        }
    
    character = memory["characters"][character_name]
    
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
    
    save_current_memory(story_id, memory)
    return memory

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
        "timestamp": datetime.utcnow().isoformat(),
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
        "timestamp": datetime.utcnow().isoformat(),
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

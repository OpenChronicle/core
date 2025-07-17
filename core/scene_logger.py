import os
import json
from datetime import datetime, timezone
from pathlib import Path
from .database import get_connection, execute_query, execute_update, init_database

def generate_scene_id():
    import time
    return str(int(time.time() * 1000000))  # Use microseconds for uniqueness

def save_scene(story_id, user_input, model_output, memory_snapshot=None, flags=None, context_refs=None, analysis_data=None, scene_label=None):
    """Save a scene to the database."""
    init_database(story_id)
    
    scene_id = generate_scene_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Prepare analysis data for storage
    analysis_json = json.dumps(analysis_data) if analysis_data else None
    
    execute_update(story_id, '''
        INSERT OR REPLACE INTO scenes 
        (scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs, analysis, scene_label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        scene_id,
        timestamp,
        user_input,
        model_output,
        json.dumps(memory_snapshot or {}),
        json.dumps(flags or []),
        json.dumps(context_refs or []),
        analysis_json,
        scene_label
    ))
    
    return scene_id

def load_scene(story_id, scene_id):
    """Load a scene from the database."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs, scene_label
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
        "scene_label": row["scene_label"]
    }

def list_scenes(story_id):
    """List all scene IDs for a story."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, scene_label FROM scenes ORDER BY timestamp ASC
    ''')
    
    return [{
        "scene_id": row["scene_id"],
        "timestamp": row["timestamp"],
        "scene_label": row["scene_label"]
    } for row in rows]

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
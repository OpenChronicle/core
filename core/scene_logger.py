import os
import json
from datetime import datetime
from pathlib import Path
from .database import get_connection, execute_query, execute_update, init_database

def generate_scene_id():
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")

def save_scene(story_id, user_input, model_output, memory_snapshot=None, flags=None, context_refs=None, analysis_data=None):
    """Save a scene to the database."""
    init_database(story_id)
    
    scene_id = generate_scene_id()
    timestamp = datetime.utcnow().isoformat()
    
    # Prepare analysis data for storage
    analysis_json = json.dumps(analysis_data) if analysis_data else None
    
    execute_update(story_id, '''
        INSERT OR REPLACE INTO scenes 
        (scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs, analysis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        scene_id,
        timestamp,
        user_input,
        model_output,
        json.dumps(memory_snapshot or {}),
        json.dumps(flags or []),
        json.dumps(context_refs or []),
        analysis_json
    ))
    
    return scene_id

def load_scene(story_id, scene_id):
    """Load a scene from the database."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs
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
        "canon_refs": json.loads(row["canon_refs"] or "[]")
    }

def list_scenes(story_id):
    """List all scene IDs for a story."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id FROM scenes ORDER BY timestamp ASC
    ''')
    
    return [row["scene_id"] for row in rows]

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
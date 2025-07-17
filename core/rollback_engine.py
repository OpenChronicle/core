import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from .scene_logger import load_scene, list_scenes
from .memory_manager import restore_memory_from_snapshot
from .database import get_connection, execute_query, execute_update, init_database

def create_rollback_point(story_id, scene_id, description="Manual rollback point"):
    """Create a rollback point at a specific scene."""
    init_database(story_id)
    
    # Verify scene exists
    scene_data = load_scene(story_id, scene_id)
    
    rollback_id = f"rollback_{scene_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    execute_update(story_id, '''
        INSERT OR REPLACE INTO rollback_points 
        (rollback_id, scene_id, timestamp, description, scene_data)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        rollback_id,
        scene_id,
        datetime.utcnow().isoformat(),
        description,
        json.dumps(scene_data)
    ))
    
    return {
        "id": rollback_id,
        "scene_id": scene_id,
        "timestamp": datetime.utcnow().isoformat(),
        "description": description,
        "scene_data": scene_data,
        "created_at": datetime.utcnow().isoformat()
    }

def list_rollback_points(story_id):
    """List all available rollback points."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT rollback_id, scene_id, timestamp, description, scene_data
        FROM rollback_points ORDER BY timestamp DESC
    ''')
    
    rollback_points = []
    for row in rows:
        rollback_points.append({
            "id": row["rollback_id"],
            "scene_id": row["scene_id"],
            "timestamp": row["timestamp"],
            "description": row["description"],
            "scene_data": json.loads(row["scene_data"])
        })
    
    return rollback_points

def get_scenes_after(story_id, target_scene_id):
    """Get all scenes that come after a target scene."""
    all_scenes = list_scenes(story_id)
    
    try:
        target_index = all_scenes.index(target_scene_id)
        return all_scenes[target_index + 1:]
    except ValueError:
        raise ValueError(f"Scene {target_scene_id} not found in story {story_id}")

def backup_scenes_for_rollback(story_id, scenes_to_backup):
    """Backup scenes before rollback."""
    if not scenes_to_backup:
        return
    
    init_database(story_id)
    backup_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    for scene_id in scenes_to_backup:
        scene_data = load_scene(story_id, scene_id)
        
        execute_update(story_id, '''
            INSERT INTO rollback_backups 
            (backup_id, scene_id, scene_data, reason)
            VALUES (?, ?, ?, ?)
        ''', (
            backup_id,
            scene_id,
            json.dumps(scene_data),
            "rollback_preparation"
        ))

def rollback_to_scene(story_id, target_scene_id, create_backup=True):
    """Rollback story to a specific scene."""
    init_database(story_id)
    
    # Verify target scene exists
    target_scene = load_scene(story_id, target_scene_id)
    
    # Get scenes that will be removed
    scenes_to_remove = get_scenes_after(story_id, target_scene_id)
    
    if not scenes_to_remove:
        return {
            "success": True,
            "message": "Already at target scene",
            "scenes_removed": 0,
            "target_scene": target_scene_id
        }
    
    # Create backup if requested
    if create_backup:
        backup_scenes_for_rollback(story_id, scenes_to_remove)
    
    # Remove scenes after target
    removed_count = 0
    for scene_id in scenes_to_remove:
        rows_affected = execute_update(story_id, '''
            DELETE FROM scenes WHERE scene_id = ?
        ''', (scene_id,))
        if rows_affected > 0:
            removed_count += 1
    
    # Restore memory state from target scene
    try:
        restore_memory_from_snapshot(story_id, target_scene_id)
        memory_restored = True
        memory_error = None
    except (FileNotFoundError, ValueError) as e:
        memory_restored = False
        memory_error = str(e)
    
    result = {
        "success": True,
        "message": f"Rolled back to scene {target_scene_id}",
        "scenes_removed": removed_count,
        "target_scene": target_scene_id,
        "memory_restored": memory_restored
    }
    
    if not memory_restored:
        result["memory_error"] = memory_error
    
    return result

def rollback_to_timestamp(story_id, target_timestamp, create_backup=True):
    """Rollback to the scene closest to a specific timestamp."""
    init_database(story_id)
    
    # Find the scene closest to the target timestamp
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp FROM scenes 
        WHERE timestamp <= ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (target_timestamp,))
    
    if not rows:
        raise ValueError(f"No scene found before timestamp {target_timestamp}")
    
    target_scene_id = rows[0]["scene_id"]
    return rollback_to_scene(story_id, target_scene_id, create_backup)

def get_rollback_candidates(story_id, limit=10):
    """Get recent scenes that are good rollback candidates."""
    init_database(story_id)
    
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp, input, flags, memory_snapshot
        FROM scenes ORDER BY timestamp DESC LIMIT ?
    ''', (limit,))
    
    candidates = []
    for row in rows:
        candidates.append({
            "scene_id": row["scene_id"],
            "timestamp": row["timestamp"],
            "input_preview": row["input"][:100] + "..." if len(row["input"]) > 100 else row["input"],
            "has_flags": bool(json.loads(row["flags"] or "[]")),
            "memory_snapshot": bool(json.loads(row["memory_snapshot"] or "{}"))
        })
    
    return candidates

def validate_rollback_integrity(story_id):
    """Validate that rollback data is consistent."""
    init_database(story_id)
    issues = []
    
    # Check scene continuity
    rows = execute_query(story_id, '''
        SELECT scene_id, timestamp FROM scenes ORDER BY timestamp ASC
    ''')
    
    if not rows:
        issues.append("No scenes found")
        return issues
    
    # Check for timestamp sequence
    for i, row in enumerate(rows[:-1]):
        current_time = datetime.fromisoformat(row["timestamp"])
        next_time = datetime.fromisoformat(rows[i + 1]["timestamp"])
        
        # Handle timezone-aware/naive comparison
        if current_time.tzinfo is None and next_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=next_time.tzinfo)
        elif current_time.tzinfo is not None and next_time.tzinfo is None:
            next_time = next_time.replace(tzinfo=current_time.tzinfo)
        
        if current_time >= next_time:
            issues.append(f"Scene {row['scene_id']} timestamp is not before {rows[i + 1]['scene_id']}")
    
    # Check rollback points
    rollback_rows = execute_query(story_id, '''
        SELECT rollback_id, scene_id FROM rollback_points
    ''')
    
    scene_ids = [row["scene_id"] for row in rows]
    
    for rollback_row in rollback_rows:
        if rollback_row["scene_id"] not in scene_ids:
            issues.append(f"Rollback point {rollback_row['rollback_id']} references non-existent scene")
    
    return issues

def cleanup_old_rollback_data(story_id, days_to_keep=30):
    """Clean up old rollback data and backups."""
    init_database(story_id)
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    cutoff_timestamp = cutoff_date.isoformat()
    
    # Clean old rollback points
    rollback_cleaned = execute_update(story_id, '''
        DELETE FROM rollback_points 
        WHERE created_at < ?
    ''', (cutoff_timestamp,))
    
    # Clean old backups
    backup_cleaned = execute_update(story_id, '''
        DELETE FROM rollback_backups 
        WHERE created_at < ?
    ''', (cutoff_timestamp,))
    
    total_cleaned = rollback_cleaned + backup_cleaned
    
    return {
        "cleaned": total_cleaned,
        "message": f"Cleaned {total_cleaned} old rollback items"
    }

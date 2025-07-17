import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

def get_db_path(story_id):
    """Get the path to the SQLite database for a story."""
    return os.path.join("storage", story_id, "openchronicle.db")

def ensure_db_dir(story_id):
    """Ensure the database directory exists."""
    db_path = get_db_path(story_id)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

def init_database(story_id):
    """Initialize the database with required tables."""
    ensure_db_dir(story_id)
    db_path = get_db_path(story_id)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Create scenes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scenes (
                scene_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                input TEXT NOT NULL,
                output TEXT NOT NULL,
                memory_snapshot TEXT,
                flags TEXT,
                canon_refs TEXT,
                analysis TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if analysis column exists and add if not (for backwards compatibility)
        cursor.execute("PRAGMA table_info(scenes)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'analysis' not in columns:
            cursor.execute('ALTER TABLE scenes ADD COLUMN analysis TEXT')
        
        # Create memory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id TEXT NOT NULL,
                type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(story_id, type, key)
            )
        ''')
        
        # Create memory_history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scene_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                memory_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create rollback_points table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rollback_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rollback_id TEXT UNIQUE NOT NULL,
                scene_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                description TEXT NOT NULL,
                scene_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create rollback_backups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rollback_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_id TEXT NOT NULL,
                scene_id TEXT NOT NULL,
                scene_data TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scenes_timestamp ON scenes(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_story_type ON memory(story_id, type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_history_scene ON memory_history(scene_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rollback_scene ON rollback_points(scene_id)')
        
        conn.commit()

def get_connection(story_id):
    """Get a database connection for a story."""
    init_database(story_id)
    db_path = get_db_path(story_id)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def execute_query(story_id, query, params=None):
    """Execute a query and return results."""
    with get_connection(story_id) as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

def execute_update(story_id, query, params=None):
    """Execute an update/insert query."""
    with get_connection(story_id) as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.rowcount

def migrate_from_json(story_id):
    """Migrate existing JSON data to SQLite."""
    # Check if there's existing JSON data to migrate
    scenes_dir = os.path.join("storage", story_id, "scenes")
    memory_dir = os.path.join("storage", story_id, "memory")
    rollback_dir = os.path.join("storage", story_id, "rollback")
    
    if not any(os.path.exists(d) for d in [scenes_dir, memory_dir, rollback_dir]):
        return {"migrated": 0, "message": "No JSON data to migrate"}
    
    migrated_count = 0
    
    with get_connection(story_id) as conn:
        cursor = conn.cursor()
        
        # Migrate scenes
        if os.path.exists(scenes_dir):
            for scene_file in os.listdir(scenes_dir):
                if scene_file.endswith('.json'):
                    scene_path = os.path.join(scenes_dir, scene_file)
                    with open(scene_path, 'r', encoding='utf-8') as f:
                        scene_data = json.load(f)
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO scenes 
                        (scene_id, timestamp, input, output, memory_snapshot, flags, canon_refs)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        scene_data['scene_id'],
                        scene_data['timestamp'],
                        scene_data['input'],
                        scene_data['output'],
                        json.dumps(scene_data.get('memory', {})),
                        json.dumps(scene_data.get('flags', [])),
                        json.dumps(scene_data.get('canon_refs', []))
                    ))
                    migrated_count += 1
        
        # Migrate memory
        if os.path.exists(memory_dir):
            current_memory_path = os.path.join(memory_dir, "current_memory.json")
            if os.path.exists(current_memory_path):
                with open(current_memory_path, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
                
                # Store different memory types
                for memory_type, data in memory_data.items():
                    if memory_type != "metadata":
                        cursor.execute('''
                            INSERT OR REPLACE INTO memory 
                            (story_id, type, key, value, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            story_id,
                            memory_type,
                            "current",
                            json.dumps(data),
                            datetime.utcnow().isoformat()
                        ))
                        migrated_count += 1
            
            # Migrate memory history
            history_path = os.path.join(memory_dir, "memory_history.json")
            if os.path.exists(history_path):
                with open(history_path, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)
                
                for snapshot in history_data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO memory_history 
                        (scene_id, timestamp, memory_data)
                        VALUES (?, ?, ?)
                    ''', (
                        snapshot['scene_id'],
                        snapshot['timestamp'],
                        json.dumps(snapshot['memory'])
                    ))
                    migrated_count += 1
        
        conn.commit()
    
    return {"migrated": migrated_count, "message": f"Migrated {migrated_count} records to SQLite"}

def cleanup_json_files(story_id):
    """Clean up old JSON files after successful migration."""
    scenes_dir = os.path.join("storage", story_id, "scenes")
    memory_dir = os.path.join("storage", story_id, "memory")
    rollback_dir = os.path.join("storage", story_id, "rollback")
    
    cleaned_count = 0
    
    for directory in [scenes_dir, memory_dir, rollback_dir]:
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.endswith('.json'):
                    file_path = os.path.join(directory, file)
                    os.remove(file_path)
                    cleaned_count += 1
    
    return {"cleaned": cleaned_count, "message": f"Cleaned {cleaned_count} JSON files"}

def get_database_stats(story_id):
    """Get database statistics."""
    with get_connection(story_id) as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Count scenes
        cursor.execute("SELECT COUNT(*) FROM scenes")
        stats['scenes_count'] = cursor.fetchone()[0]
        
        # Count memory entries
        cursor.execute("SELECT COUNT(*) FROM memory")
        stats['memory_entries'] = cursor.fetchone()[0]
        
        # Count memory history
        cursor.execute("SELECT COUNT(*) FROM memory_history")
        stats['memory_history_count'] = cursor.fetchone()[0]
        
        # Count rollback points
        cursor.execute("SELECT COUNT(*) FROM rollback_points")
        stats['rollback_points_count'] = cursor.fetchone()[0]
        
        # Database size
        db_path = get_db_path(story_id)
        if os.path.exists(db_path):
            stats['database_size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
        else:
            stats['database_size_mb'] = 0
        
        return stats

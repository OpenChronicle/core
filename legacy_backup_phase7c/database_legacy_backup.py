import sqlite3
import json
import os
from datetime import datetime, UTC
from pathlib import Path

def has_fts5_support():
    """Check if SQLite supports FTS5."""
    try:
        with sqlite3.connect(':memory:') as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
            cursor.execute("DROP TABLE test_fts")
            return True
    except sqlite3.OperationalError:
        return False

def _is_test_context():
    """Detect if we're running in a test context."""
    import sys
    # Check if pytest is running
    return 'pytest' in sys.modules or 'unittest' in sys.modules

def get_db_path(story_id, is_test=None):
    """Get the path to the SQLite database for a story.
    
    Args:
        story_id: The story identifier
        is_test: Whether this is for test data. If None, auto-detects test context.
    """
    if is_test is None:
        is_test = _is_test_context()
    
    if is_test:
        # Test data goes in temp folder
        return os.path.join("storage", "temp", "test_data", story_id, "openchronicle.db")
    else:
        # Production data goes in storypacks
        return os.path.join("storage", "storypacks", story_id, "openchronicle.db")

def ensure_db_dir(story_id, is_test=None):
    """Ensure the database directory exists."""
    db_path = get_db_path(story_id, is_test)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

def init_database(story_id, is_test=None):
    """Initialize the database with required tables."""
    ensure_db_dir(story_id, is_test)
    db_path = get_db_path(story_id, is_test)
    
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
        
        # Check if scene_label column exists and add if not
        if 'scene_label' not in columns:
            cursor.execute('ALTER TABLE scenes ADD COLUMN scene_label TEXT')
        
        # Check if structured_tags column exists and add if not
        if 'structured_tags' not in columns:
            cursor.execute('ALTER TABLE scenes ADD COLUMN structured_tags TEXT')
        
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
        
        # Create bookmarks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_id TEXT NOT NULL,
                scene_id TEXT NOT NULL,
                label TEXT NOT NULL,
                description TEXT,
                bookmark_type TEXT DEFAULT 'user',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scenes_timestamp ON scenes(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scenes_label ON scenes(scene_label)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_story_type ON memory(story_id, type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_history_scene ON memory_history(scene_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rollback_scene ON rollback_points(scene_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_story ON bookmarks(story_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_scene ON bookmarks(scene_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_type ON bookmarks(bookmark_type)')
        
        # Create FTS5 virtual tables for full-text search
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS scenes_fts USING fts5(
                scene_id UNINDEXED,
                input,
                output,
                scene_label,
                flags,
                analysis,
                content='scenes',
                content_rowid='rowid'
            )
        ''')
        
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                memory_id UNINDEXED,
                story_id UNINDEXED,
                type UNINDEXED,
                key,
                value
            )
        ''')
        
        # Create triggers for automatic FTS5 indexing
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS scenes_ai AFTER INSERT ON scenes BEGIN
                INSERT INTO scenes_fts(rowid, scene_id, input, output, scene_label, flags, analysis)
                VALUES (new.rowid, new.scene_id, new.input, new.output, 
                        COALESCE(new.scene_label, ''), COALESCE(new.flags, ''), COALESCE(new.analysis, ''));
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS scenes_ad AFTER DELETE ON scenes BEGIN
                INSERT INTO scenes_fts(scenes_fts, rowid, scene_id, input, output, scene_label, flags, analysis)
                VALUES ('delete', old.rowid, old.scene_id, old.input, old.output, 
                        COALESCE(old.scene_label, ''), COALESCE(old.flags, ''), COALESCE(old.analysis, ''));
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS scenes_au AFTER UPDATE ON scenes BEGIN
                INSERT INTO scenes_fts(scenes_fts, rowid, scene_id, input, output, scene_label, flags, analysis)
                VALUES ('delete', old.rowid, old.scene_id, old.input, old.output, 
                        COALESCE(old.scene_label, ''), COALESCE(old.flags, ''), COALESCE(old.analysis, ''));
                INSERT INTO scenes_fts(rowid, scene_id, input, output, scene_label, flags, analysis)
                VALUES (new.rowid, new.scene_id, new.input, new.output, 
                        COALESCE(new.scene_label, ''), COALESCE(new.flags, ''), COALESCE(new.analysis, ''));
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
                INSERT INTO memory_fts(memory_id, story_id, type, key, value)
                VALUES (new.id, new.story_id, new.type, new.key, new.value);
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
                DELETE FROM memory_fts WHERE memory_id = old.id;
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory BEGIN
                DELETE FROM memory_fts WHERE memory_id = old.id;
                INSERT INTO memory_fts(memory_id, story_id, type, key, value)
                VALUES (new.id, new.story_id, new.type, new.key, new.value);
            END
        ''')
        
        # Populate FTS5 tables with existing data
        cursor.execute('''
            INSERT OR IGNORE INTO scenes_fts(rowid, scene_id, input, output, scene_label, flags, analysis)
            SELECT rowid, scene_id, input, output, 
                   COALESCE(scene_label, ''), COALESCE(flags, ''), COALESCE(analysis, '') 
            FROM scenes
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO memory_fts(memory_id, story_id, type, key, value)
            SELECT id, story_id, type, key, value FROM memory
        ''')
        
        conn.commit()

def get_connection(story_id, is_test=None):
    """Get a database connection for a story."""
    # Only initialize database if it doesn't exist
    db_path = get_db_path(story_id, is_test)
    if not os.path.exists(db_path):
        init_database(story_id, is_test)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def execute_query(story_id, query, params=None, is_test=None):
    """Execute a query and return results."""
    with get_connection(story_id, is_test) as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

def execute_update(story_id, query, params=None, is_test=None):
    """Execute an update/insert query."""
    with get_connection(story_id, is_test) as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.rowcount

def execute_insert(story_id, query, params=None, is_test=None):
    """Execute an insert query and return the last row ID."""
    with get_connection(story_id, is_test) as conn:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.lastrowid

def migrate_from_json(story_id):
    """Migrate existing JSON data to SQLite."""
    # Check if there's existing JSON data to migrate
    scenes_dir = os.path.join("storage", "temp", "test_data", story_id, "scenes")
    memory_dir = os.path.join("storage", "temp", "test_data", story_id, "memory")
    rollback_dir = os.path.join("storage", "temp", "test_data", story_id, "rollback")
    
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
                            datetime.now(UTC).isoformat()
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
    scenes_dir = os.path.join("storage", "temp", "test_data", story_id, "scenes")
    memory_dir = os.path.join("storage", "temp", "test_data", story_id, "memory")
    rollback_dir = os.path.join("storage", "temp", "test_data", story_id, "rollback")
    
    cleaned_count = 0
    
    for directory in [scenes_dir, memory_dir, rollback_dir]:
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.endswith('.json'):
                    file_path = os.path.join(directory, file)
                    os.remove(file_path)
                    cleaned_count += 1
    
    return {"cleaned": cleaned_count, "message": f"Cleaned {cleaned_count} JSON files"}

def get_database_stats(story_id, is_test=None):
    """Get database statistics."""
    with get_connection(story_id, is_test) as conn:
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
        db_path = get_db_path(story_id, is_test)
        if os.path.exists(db_path):
            stats['database_size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
        else:
            stats['database_size_mb'] = 0
        
        return stats

def optimize_fts_index(story_id, is_test=None):
    """Optimize FTS5 indexes for better performance."""
    with get_connection(story_id, is_test) as conn:
        cursor = conn.cursor()
        
        # Optimize scenes FTS5 index
        cursor.execute("INSERT INTO scenes_fts(scenes_fts) VALUES('optimize')")
        
        # Optimize memory FTS5 index
        cursor.execute("INSERT INTO memory_fts(memory_fts) VALUES('optimize')")
        
        conn.commit()

def rebuild_fts_index(story_id, is_test=None):
    """Rebuild FTS5 indexes from scratch."""
    with get_connection(story_id, is_test) as conn:
        cursor = conn.cursor()
        
        # Rebuild scenes FTS5 index
        cursor.execute("INSERT INTO scenes_fts(scenes_fts) VALUES('rebuild')")
        
        # Rebuild memory FTS5 index
        cursor.execute("INSERT INTO memory_fts(memory_fts) VALUES('rebuild')")
        
        conn.commit()

def get_fts_stats(story_id, is_test=None):
    """Get FTS5 index statistics."""
    with get_connection(story_id, is_test) as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Check if FTS5 tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%_fts'
        """)
        fts_tables = [row[0] for row in cursor.fetchall()]
        stats['fts_tables'] = fts_tables
        
        # Get FTS5 table sizes
        for table in fts_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f'{table}_entries'] = cursor.fetchone()[0]
        
        return stats

def check_fts_support():
    """Check if FTS5 is supported in the current SQLite version."""
    try:
        with sqlite3.connect(":memory:") as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
            cursor.execute("DROP TABLE test_fts")
            return True
    except sqlite3.OperationalError:
        return False

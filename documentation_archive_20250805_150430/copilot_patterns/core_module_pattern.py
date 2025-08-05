"""
OpenChronicle Core Module Pattern

This file demonstrates the standard pattern for OpenChronicle core modules.
Use this as a template when creating new core modules.
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from datetime import datetime

# Standard imports for OpenChronicle modules
from core.database import DatabaseManager
from utilities.logging_system import get_logger

@dataclass
class ModuleConfig:
    """Standard configuration dataclass pattern"""
    enabled: bool = True
    debug_mode: bool = False
    cache_size: int = 1000
    timeout: int = 30
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModuleConfig':
        """Create config from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

class CoreModuleTemplate:
    """
    Template for OpenChronicle core modules
    
    Standard patterns:
    - Database integration via DatabaseManager
    - Logging via utilities.logging_system
    - Configuration via dataclass
    - Error handling with custom exceptions
    - Type hints throughout
    - Async support where appropriate
    """
    
    def __init__(self, story_id: str, config: Optional[ModuleConfig] = None):
        """Initialize with story_id and optional config"""
        self.story_id = story_id
        self.config = config or ModuleConfig()
        self.logger = get_logger(f"{self.__class__.__name__}_{story_id}")
        
        # Database connection
        self.db_manager = DatabaseManager(story_id)
        
        # Module state
        self._initialized = False
        self._cache = {}
        
        self.logger.info(f"Initialized {self.__class__.__name__} for story: {story_id}")
    
    def initialize(self) -> None:
        """Initialize module - call after construction"""
        if self._initialized:
            return
            
        try:
            self._setup_database()
            self._load_initial_data()
            self._initialized = True
            self.logger.info("Module initialization complete")
        except Exception as e:
            self.logger.error(f"Failed to initialize module: {e}")
            raise
    
    def _setup_database(self) -> None:
        """Setup database tables/indexes for this module"""
        # Example table creation
        self.db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS module_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        self.db_manager.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_module_data_key ON module_data(key)
        """)
    
    def _load_initial_data(self) -> None:
        """Load initial data/state for module"""
        pass
    
    def get_data(self, key: str) -> Optional[Any]:
        """Get data with caching pattern"""
        if key in self._cache:
            return self._cache[key]
        
        result = self.db_manager.fetch_one(
            "SELECT value FROM module_data WHERE key = ?",
            (key,)
        )
        
        if result:
            try:
                value = json.loads(result['value'])
                self._cache[key] = value
                return value
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid JSON for key {key}")
                return None
        
        return None
    
    def set_data(self, key: str, value: Any) -> None:
        """Set data with caching pattern"""
        json_value = json.dumps(value)
        
        self.db_manager.execute_query("""
            INSERT OR REPLACE INTO module_data (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, json_value))
        
        self._cache[key] = value
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self._cache.clear()
        self.logger.info("Module cleanup complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get module statistics"""
        return {
            'story_id': self.story_id,
            'initialized': self._initialized,
            'cache_size': len(self._cache),
            'config': asdict(self.config)
        }

# Example usage and testing pattern
if __name__ == "__main__":
    # Standard test pattern for modules
    import tempfile
    import os
    
    # Create temporary story for testing
    test_story_id = "test_story_123"
    
    # Initialize module
    module = CoreModuleTemplate(test_story_id)
    module.initialize()
    
    # Test basic functionality
    module.set_data("test_key", {"example": "data"})
    retrieved = module.get_data("test_key")
    assert retrieved == {"example": "data"}
    
    # Test stats
    stats = module.get_stats()
    assert stats['story_id'] == test_story_id
    assert stats['initialized'] is True
    
    # Cleanup
    module.cleanup()
    
    print("✅ Module pattern test passed")

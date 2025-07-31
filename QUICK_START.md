# Quick Start: Begin Refactoring Today

**Time to Start**: 5 minutes  
**First Checkpoint**: End of day  
**Phase 1 Goal**: 8-10 days  

## Immediate Actions (Next 30 minutes)

### 1. Create Feature Branch
```powershell
# Navigate to project root
cd "c:\Users\carl.yeager\OneDrive\Documents\GitHub\OpenChronicle\openchronicle-core"

# Create and switch to refactoring branch
git checkout -b refactor/core-modules-overhaul

# Verify branch creation
git branch
```

### 2. Set Up Directory Structure
```powershell
# Create shared infrastructure directory
New-Item -ItemType Directory -Path "core\shared" -Force

# Create model management directory  
New-Item -ItemType Directory -Path "core\model_management" -Force

# Verify directories created
Get-ChildItem "core" -Directory
```

### 3. Create Initial Files
```powershell
# Create placeholder files for Phase 1
New-Item -ItemType File -Path "core\shared\__init__.py" -Force
New-Item -ItemType File -Path "core\shared\database_operations.py" -Force
New-Item -ItemType File -Path "core\shared\json_utilities.py" -Force
New-Item -ItemType File -Path "core\shared\search_utilities.py" -Force
New-Item -ItemType File -Path "core\shared\validation.py" -Force

New-Item -ItemType File -Path "core\model_management\__init__.py" -Force
New-Item -ItemType File -Path "core\model_management\base_adapter.py" -Force
New-Item -ItemType File -Path "core\model_management\adapter_registry.py" -Force
New-Item -ItemType File -Path "core\model_management\adapter_interfaces.py" -Force

# Verify files created
Get-ChildItem "core\shared" -File
Get-ChildItem "core\model_management" -File
```

## Today's Focus: Database Operations (Day 1)

### Step 1: Analyze Current Database Patterns (30 minutes)

**Goal**: Understand what needs to be consolidated.

#### Scan for database patterns:
```powershell
# Find all database-related code
grep -r "sqlite3\|execute.*query\|\.cursor()" core/ --include="*.py"

# Find all connection patterns
grep -r "get_connection\|Connection" core/ --include="*.py"
```

#### Key modules to examine:
1. `core/database.py` - Primary database module
2. `core/scene_logger.py` - Scene storage
3. `core/memory_manager.py` - Memory persistence

### Step 2: Create DatabaseOperations Base Class (2 hours)

Create `core/shared/database_operations.py`:

```python
"""
Shared database operations for OpenChronicle core modules.
Consolidates database patterns from 10+ modules to eliminate duplication.
"""

import sqlite3
import json
import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from contextlib import contextmanager

class DatabaseOperations:
    """Base class for all database operations."""
    
    def __init__(self, story_id: str, is_test: bool = None):
        self.story_id = story_id
        self.is_test = is_test if is_test is not None else self._is_test_context()
        self.db_path = self._get_db_path()
        
    def _is_test_context(self) -> bool:
        """Detect if running in test context."""
        import sys
        return 'pytest' in sys.modules or os.getenv('TESTING') == '1'
    
    def _get_db_path(self) -> str:
        """Get database path based on story_id and test context."""
        if self.is_test:
            base_dir = Path("storage/temp/test_data") / self.story_id
        else:
            base_dir = Path("storage/data") / self.story_id
        
        base_dir.mkdir(parents=True, exist_ok=True)
        return str(base_dir / "story.db")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute UPDATE/DELETE query."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
                return True
        except sqlite3.Error:
            return False
    
    def execute_insert(self, query: str, params: tuple = None) -> Optional[int]:
        """Execute INSERT query and return row ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error:
            return None

class QueryBuilder:
    """Dynamic SQL query construction."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder state."""
        self._select = []
        self._from = ""
        self._where = []
        self._order_by = []
        self._limit = None
        self._params = []
        return self
    
    def select(self, columns: Union[str, List[str]]):
        """Add SELECT columns."""
        if isinstance(columns, str):
            self._select.append(columns)
        else:
            self._select.extend(columns)
        return self
    
    def from_table(self, table: str):
        """Set FROM table."""
        self._from = table
        return self
    
    def where(self, condition: str, *params):
        """Add WHERE condition."""
        self._where.append(condition)
        self._params.extend(params)
        return self
    
    def order_by(self, column: str, direction: str = "ASC"):
        """Add ORDER BY clause."""
        self._order_by.append(f"{column} {direction}")
        return self
    
    def limit(self, count: int):
        """Add LIMIT clause."""
        self._limit = count
        return self
    
    def build(self) -> tuple[str, tuple]:
        """Build the final query and parameters."""
        query_parts = []
        
        # SELECT
        if self._select:
            query_parts.append(f"SELECT {', '.join(self._select)}")
        
        # FROM
        if self._from:
            query_parts.append(f"FROM {self._from}")
        
        # WHERE
        if self._where:
            query_parts.append(f"WHERE {' AND '.join(self._where)}")
        
        # ORDER BY
        if self._order_by:
            query_parts.append(f"ORDER BY {', '.join(self._order_by)}")
        
        # LIMIT
        if self._limit:
            query_parts.append(f"LIMIT {self._limit}")
        
        return " ".join(query_parts), tuple(self._params)

# Convenience functions for backward compatibility
def get_db_path(story_id: str, is_test: bool = None) -> str:
    """Get database path for story."""
    db_ops = DatabaseOperations(story_id, is_test)
    return db_ops.db_path

def get_connection(story_id: str, is_test: bool = None):
    """Get database connection for story."""
    db_ops = DatabaseOperations(story_id, is_test)
    return db_ops.get_connection()

def execute_query(story_id: str, query: str, params: tuple = None, is_test: bool = None) -> List[Dict[str, Any]]:
    """Execute query for story."""
    db_ops = DatabaseOperations(story_id, is_test)
    return db_ops.execute_query(query, params)

def execute_update(story_id: str, query: str, params: tuple = None, is_test: bool = None) -> bool:
    """Execute update for story."""
    db_ops = DatabaseOperations(story_id, is_test)
    return db_ops.execute_update(query, params)

def execute_insert(story_id: str, query: str, params: tuple = None, is_test: bool = None) -> Optional[int]:
    """Execute insert for story."""
    db_ops = DatabaseOperations(story_id, is_test)
    return db_ops.execute_insert(query, params)
```

### Step 3: Create Initial Tests (1 hour)

Create `tests/test_shared_database_operations.py`:

```python
"""Tests for shared database operations."""

import pytest
import tempfile
import os
from pathlib import Path

from core.shared.database_operations import DatabaseOperations, QueryBuilder

@pytest.fixture
def temp_story_id():
    """Create temporary story ID for testing."""
    return "test_story_" + str(os.getpid())

def test_database_operations_init(temp_story_id):
    """Test DatabaseOperations initialization."""
    db_ops = DatabaseOperations(temp_story_id, is_test=True)
    assert db_ops.story_id == temp_story_id
    assert db_ops.is_test is True
    assert "test_data" in db_ops.db_path

def test_query_builder():
    """Test QueryBuilder functionality."""
    builder = QueryBuilder()
    query, params = (builder
                    .select(["id", "name"])
                    .from_table("users")
                    .where("age > ?", 18)
                    .where("status = ?", "active")
                    .order_by("name")
                    .limit(10)
                    .build())
    
    expected = "SELECT id, name FROM users WHERE age > ? AND status = ? ORDER BY name ASC LIMIT 10"
    assert query == expected
    assert params == (18, "active")
```

### Step 4: Test and Validate (30 minutes)

```powershell
# Run the new tests
python -m pytest tests/test_shared_database_operations.py -v

# Verify no regressions in existing tests
python -m pytest tests/test_database.py -v

# Quick validation that imports work
python -c "from core.shared.database_operations import DatabaseOperations; print('✓ Database operations module working')"
```

## End of Day 1 Checkpoint

### Validation Checklist:
- [ ] New directory structure created
- [ ] `DatabaseOperations` class implemented
- [ ] `QueryBuilder` class implemented  
- [ ] Basic tests created and passing
- [ ] No regressions in existing functionality
- [ ] Feature branch created and committed

### Git Commit:
```powershell
# Add new files
git add core/shared/
git add tests/test_shared_database_operations.py
git add REFACTORING_STRATEGY.md
git add PHASE_1_CHECKLIST.md

# Commit Phase 1 Day 1 progress
git commit -m "Phase 1 Day 1: Create shared database operations

- Create core/shared directory structure
- Implement DatabaseOperations base class
- Implement QueryBuilder for dynamic queries
- Add connection management and error handling
- Create initial test suite
- Maintain backward compatibility

Next: Day 2 - JSON utilities consolidation"
```

## Tomorrow (Day 2): JSON Utilities

**Focus**: Create `core/shared/json_utilities.py` to eliminate JSON handling duplication.

**Preparation**: 
1. Scan for JSON patterns: `grep -r "json\." core/ --include="*.py"`
2. Identify common serialization needs
3. Plan schema validation approach

## Quick Progress Check

At any point, verify progress:

```powershell
# Check file structure
Get-ChildItem "core\shared", "core\model_management" -Recurse

# Verify tests pass
python -m pytest tests/test_shared_database_operations.py -v

# Check for any issues
python -c "import core.shared.database_operations; print('✓ Module imports successfully')"
```

---

**You can start this refactoring immediately with minimal risk. Each day builds incrementally on the previous day's work, and the system remains fully functional throughout the process.**

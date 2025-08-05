# LEGACY CODE CLEANUP PLAN

**Date**: August 5, 2025  
**Priority**: HIGH - Immediate cleanup required  
**Philosophy**: NO BACKWARDS COMPATIBILITY - Remove all legacy patterns  

---

## ⚠️ **CRITICAL FINDINGS** ⚠️

Based on codebase analysis, we have **EXTENSIVE legacy compatibility layers** that violate our new development philosophy. These must be **ELIMINATED IMMEDIATELY**.

---

## 🗑️ **LEGACY PATTERNS TO DELETE ENTIRELY**

### **1. Scene Systems Backwards Compatibility (WORST OFFENDER)**

**File**: `core/scene_systems/scene_orchestrator.py` lines 280-340+  
**Problem**: 60+ lines of wrapper functions that duplicate orchestrator functionality  
**Action**: **DELETE ENTIRELY**

```python
# DELETE ALL OF THIS:
# ===== BACKWARD COMPATIBILITY FUNCTIONS =====
def generate_scene_id() -> str:
def save_scene(story_id: str, user_input: str, model_output: str, ...):
def load_scene(story_id: str, scene_id: str) -> Optional[Dict[str, Any]]:
def list_scenes(story_id: str) -> List[Dict[str, Any]]:
def get_scenes_with_long_turns(story_id: str) -> List[Dict[str, Any]]:
def get_scenes_by_mood(story_id: str, mood: str) -> List[Dict[str, Any]]:
def get_scenes_by_type(story_id: str, scene_type: str) -> List[Dict[str, Any]]:
def get_token_usage_stats(story_id: str) -> Dict[str, Any]:
def get_character_mood_timeline(story_id: str, character_name: str) -> List[Dict[str, Any]]:
def update_scene_label(story_id: str, scene_id: str, scene_label: str) -> bool:
def get_scenes_by_label(story_id: str, scene_label: str) -> List[Dict[str, Any]]:
```

**Replacement**: Direct use of `SceneOrchestrator` class - no wrappers needed!

### **2. JSON Utilities Backwards Compatibility**

**File**: `core/shared/json_utilities.py` lines 223-240  
**Problem**: Redundant wrapper functions for class methods  
**Action**: **DELETE ENTIRELY**

```python
# DELETE ALL OF THIS:
# Convenience functions for backward compatibility
def safe_loads(json_str: str, fallback: Any = None) -> Any:
def safe_dumps(data: Any, pretty: bool = False) -> str:
def load_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
def save_json_file(data: Any, file_path: Union[str, Path]) -> bool:
```

**Replacement**: Direct use of `JSONUtilities` class methods

### **3. Search Utilities Backwards Compatibility**

**File**: `core/shared/search_utilities.py` lines 558-600+  
**Problem**: Converting new search results back to old format  
**Action**: **DELETE ENTIRELY**

```python
# DELETE ALL OF THIS:
# Backward compatibility functions for existing code
def search_scenes_fts(story_id: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
def search_with_pagination(...) -> List[Dict[str, Any]]:
```

**Replacement**: Direct use of `SearchUtilities` class with modern result format

### **4. Database Operations Compatibility**

**File**: `core/shared/database_operations.py` line 147+  
**Problem**: Wrapper functions around class methods  
**Action**: **DELETE ENTIRELY**

```python
# DELETE: # Convenience functions for backward compatibility
```

### **5. Legacy Meta.yaml Support**

**File**: `core/story_loader.py` lines 8, 13, 37-44  
**Problem**: Supporting obsolete YAML format  
**Action**: **DELETE YAML SUPPORT ENTIRELY**

```python
# DELETE ALL meta.yaml fallback code:
# Check for meta.json first, then meta.yaml for backward compatibility
if os.path.exists(meta_json_path):
    meta_path = meta_json_path
elif os.path.exists(meta_yaml_path):  # DELETE THIS BRANCH
    meta_path = meta_yaml_path
```

**Replacement**: JSON ONLY - no fallback

### **6. Legacy Models.json Backup Support**

**File**: `utilities/backup_manager.py` lines 122-124  
**Problem**: Supporting obsolete models.json format  
**Action**: **DELETE ENTIRELY**

```python
# DELETE THIS:
# Backup legacy models.json if it exists (for compatibility)
if (self.config_dir / "models.json").exists():
    results["legacy_models"] = self.backup_config("models.json")
```

**Replacement**: Current registry format only

### **7. Storypack Importer Backwards Compatibility**

**File**: `utilities/storypack_importer.py` lines 1052-1055  
**Problem**: Wrapper method for "backwards compatibility"  
**Action**: **DELETE WRAPPER**

```python
# DELETE THIS WRAPPER:
def discover_source_files(self) -> Dict[str, List[Path]]:
    # This is a wrapper around _discover_files_in_directory for backwards compatibility.
```

**Replacement**: Direct use of `_discover_files_in_directory`

---

## 🔧 **CLEANUP IMPLEMENTATION PLAN**

### **Phase 1: Scene Systems (Day 1)**
1. **DELETE** entire backwards compatibility section (lines 280-340+)
2. **UPDATE** all calling code to use `SceneOrchestrator` directly
3. **REMOVE** module-level imports of deleted functions
4. **TEST** that all functionality works through orchestrator

### **Phase 2: Shared Utilities (Day 1)**
1. **DELETE** all `# Convenience functions for backward compatibility` sections
2. **UPDATE** calling code to use class methods directly:
   - `JSONUtilities.safe_loads()` instead of `safe_loads()`
   - `SearchUtilities().search_scenes()` instead of `search_scenes_fts()`
3. **VERIFY** no performance degradation

### **Phase 3: Story Loading (Day 2)**
1. **DELETE** all meta.yaml support code
2. **REQUIRE** meta.json for all storypacks
3. **UPDATE** documentation to reflect JSON-only requirement
4. **REMOVE** any remaining YAML dependencies

### **Phase 4: Backup Manager (Day 2)**
1. **DELETE** legacy models.json backup logic
2. **SIMPLIFY** backup process to current registry format only
3. **CLEAN UP** any legacy backup restoration code

### **Phase 5: Storypack Importer (Day 3)**
1. **DELETE** backwards compatibility wrapper methods
2. **RENAME** internal methods to public if needed
3. **UPDATE** calling code to use direct methods

---

## 📊 **IMPACT ASSESSMENT**

### **Lines of Code Reduction**
- **Scene Systems**: ~60 lines deleted
- **Shared Utilities**: ~40 lines deleted  
- **Story Loader**: ~10 lines deleted
- **Backup Manager**: ~5 lines deleted
- **Storypack Importer**: ~15 lines deleted
- **Total**: ~130 lines of legacy cruft ELIMINATED

### **Performance Benefits**
- **Reduced function call overhead** from eliminated wrappers
- **Cleaner memory footprint** - no duplicate code paths
- **Faster imports** - fewer functions to load
- **Better caching** - direct method calls

### **Code Quality Benefits**
- **Single source of truth** - no duplicate implementations
- **Clearer API surface** - use classes directly
- **Better maintainability** - fewer code paths to understand
- **Easier testing** - test orchestrators directly

---

## ⚠️ **BREAKING CHANGES (EMBRACE THEM!)**

### **Scene Systems Changes**
```python
# OLD (DELETE):
from core.scene_systems.scene_orchestrator import save_scene
result = save_scene(story_id, input_text, output_text)

# NEW (IMPLEMENT):
from core.scene_systems import SceneOrchestrator
orchestrator = SceneOrchestrator(story_id)
result = orchestrator.save_scene(input_text, output_text)
```

### **JSON Utilities Changes**
```python
# OLD (DELETE):
from core.shared.json_utilities import load_json_file
data = load_json_file(path)

# NEW (IMPLEMENT):
from core.shared.json_utilities import JSONUtilities
data = JSONUtilities.load_file(path)
```

### **Search Utilities Changes**
```python
# OLD (DELETE):
from core.shared.search_utilities import search_scenes_fts
results = search_scenes_fts(story_id, query)

# NEW (IMPLEMENT):
from core.shared.search_utilities import SearchUtilities
search_util = SearchUtilities()
results = search_util.search_scenes(story_id, query)
```

---

## 🚀 **IMPLEMENTATION COMMANDS**

### **Day 1: Scene Systems + Shared Utilities**
```powershell
# Delete backwards compatibility sections
# Update all imports and calling code
# Run tests to ensure functionality
```

### **Day 2: Story Loading + Backup Manager**
```powershell
# Remove YAML support entirely
# Simplify backup logic
# Update documentation
```

### **Day 3: Final Cleanup**
```powershell
# Remove remaining wrappers
# Clean up imports
# Full test suite validation
```

---

## ✅ **SUCCESS CRITERIA**

1. **Zero backwards compatibility functions remain**
2. **All functionality accessible through orchestrator classes**
3. **No performance degradation**
4. **All tests pass with new patterns**
5. **Codebase is cleaner and more maintainable**

---

## 🎯 **WHY THIS MATTERS**

This cleanup perfectly embodies our **NO BACKWARDS COMPATIBILITY** philosophy:

- ✅ **Replace inferior patterns** (wrappers) with superior ones (direct class usage)
- ✅ **Remove old code entirely** without transition periods
- ✅ **Use internal development advantage** to build better architecture
- ✅ **Optimize for future maintainability** over current convenience

**This is exactly the kind of breaking change we should embrace for better architecture!**

---

**Priority**: IMMEDIATE  
**Timeline**: 3 days maximum  
**Risk**: LOW (internal development, no public API)  
**Benefit**: HIGH (cleaner codebase, better performance, easier maintenance)

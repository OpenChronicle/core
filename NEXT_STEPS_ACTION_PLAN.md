# OpenChronicle Next Steps Action Plan
## Following Successful Hexagonal Test Migration

### ✅ COMPLETED SUCCESSFULLY
- **Tests folder fully migrated to hexagonal architecture** 
- **349 tests discovered and working**
- **All test imports updated**
- **Test structure compliant with hexagonal principles**

---

## 🚨 PHASE 1: Fix Critical Architecture Violations (HIGH PRIORITY)

### **Domain Layer Violations (4 files) - MUST FIX**
These violate core hexagonal principles - domain should never import from outer layers.

#### 1. Fix `domain/models/configuration_manager.py` 
**Issue**: Directly imports and instantiates `RegistryManager` from infrastructure
**Solution**: 
```bash
# Create adapter pattern
python scripts/create_registry_adapter.py
```

#### 2-4. Fix Timeline Fallback Files
**Files**: 
- `domain/services/timeline/shared/fallback_navigation.py`
- `domain/services/timeline/shared/fallback_state.py` 
- `domain/services/timeline/shared/fallback_timeline.py`

**Issue**: Commented infrastructure imports, but need proper dependency injection
**Solution**: Use `IRegistryPort` interface created above

---

## 🔧 PHASE 2: Fix Application Layer Violations (MEDIUM PRIORITY)

### **Storypack Importer Issues (9 files)**
**Issue**: Application layer importing from interfaces via relative imports
**Root Cause**: Interfaces should be in domain/ports/, not separate interfaces layer

**Solution Strategy**:
1. Move business interfaces to `domain/ports/`
2. Keep UI interfaces in `interfaces/`
3. Update imports to use dependency injection

**Files to fix**:
```
application/services/importers/storypack/generators/*.py
application/services/importers/storypack/parsers/*.py  
application/services/importers/storypack/processors/*.py
```

---

## ⚡ PHASE 3: Fix Infrastructure Violations (LOW PRIORITY)

### **Performance Module Issues (3 files)**
**Issue**: Infrastructure importing from interfaces (wrong direction)
**Files**:
- `infrastructure/performance/analysis/bottleneck_analyzer.py`
- `infrastructure/performance/metrics/collector.py`
- `infrastructure/performance/metrics/storage.py`

**Solution**: Move performance interfaces to `domain/ports/performance_port.py`

---

## 🚀 IMMEDIATE ACTIONS (Next 30 minutes)

### **1. Create Registry Adapter (5 min)**
```bash
python scripts/create_registry_adapter.py
```

### **2. Update Configuration Manager (10 min)**
```bash
# Fix the main domain violation
python scripts/fix_configuration_manager.py
```

### **3. Validate Progress (5 min)**
```bash
python scripts/validate_hexagonal_tests.py
```

### **4. Fix Storypack Imports (10 min)**
```bash
python scripts/fix_storypack_imports.py
```

---

## 📈 SUCCESS METRICS

### **Current Status**:
- **Test Compliance**: ✅ 100% (COMPLETE)
- **Architecture Compliance**: ⚠️ 63.7% (6/9 tests pass)
- **Boundary Violations**: 🚨 16 files

### **Target Status (After fixes)**:
- **Architecture Compliance**: ✅ 95%+ (8-9/9 tests pass)
- **Boundary Violations**: ✅ 0-2 files
- **Test Coverage**: Target 85%+ (currently low due to missing tests)

---

## 📋 LONG-TERM GOALS (Next Sprint)

### **1. Test Coverage Improvement**
- Add tests for 160+ uncovered source modules
- Target: 85% test coverage

### **2. Performance Optimization**
- Fix performance interface violations
- Implement proper monitoring abstractions

### **3. Documentation Updates**
- Update architecture documentation
- Create developer onboarding guide for hexagonal principles

---

## 🎯 DECISION POINTS

### **High-Impact, Low-Effort Fixes**:
1. ✅ **Domain violations** - Easy to fix with dependency injection
2. ✅ **Storypack imports** - Simple interface moves

### **Medium-Impact, Medium-Effort**:
3. ⚠️ **Performance interfaces** - Requires careful design

### **Success Criteria**: 
- All architecture validation tests pass (9/9)
- Zero hexagonal boundary violations  
- Maintains all 349 existing tests passing

**Next Command**: `python scripts/create_registry_adapter.py`

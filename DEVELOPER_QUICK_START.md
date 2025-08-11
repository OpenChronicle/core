# 🚀 OpenChronicle Developer Quick Start Guide

**Welcome to OpenChronicle!** This guide gets new developers productive in 15 minutes.

## ⚡ **Quick Setup (5 minutes)**

### **1. Prerequisites Check**
```powershell
# Verify requirements
python --version    # Need 3.12+
git --version      # Any recent version
code --version     # VS Code recommended
```

### **2. Environment Setup**
```powershell
# Clone and enter project
git clone <repo-url> openchronicle-core
cd openchronicle-core

# Install dependencies
pip install -r requirements.txt

# Validate setup
python scripts/validate_environment.py
```

**Expected Output**: `✅ All checks passed (8/8)`

## 🏗️ **Architecture Overview (5 minutes)**

### **Current State (Phase 0 - Complete)**
```
📁 Project Structure:
├── src/openchronicle/          # 🎯 NEW: Hexagonal architecture (target)
├── core/                       # ⚠️  LEGACY: Will be removed in Phase 1
├── utilities/                  # ⚠️  LEGACY: Moving to infrastructure/
├── tests/                      # ✅ Test suite (347 tests)
└── scripts/                    # ✅ Development automation
```

### **Hexagonal Architecture (Target)**
```
🏛️ Layers:
├── 🧠 Domain/          # Business logic, entities, use cases
├── 📋 Application/     # Orchestration, services, interfaces
├── 🔌 Infrastructure/ # External dependencies, data, APIs
└── 🌐 Interface/      # CLI, API, web interfaces
```

### **⚠️ CRITICAL: Migration In Progress**
- **Phase 0**: ✅ Complete (documentation, tooling, baselines)
- **Phase 1**: 🚧 **ACTIVE** - Import structure cleanup (breaking changes!)
- **Phase 2**: Import legacy core/ code to hexagonal structure
- **Phase 3**: Implement full hexagonal patterns
- **Phase 4**: Remove all legacy code

## 🧪 **Development Workflow (5 minutes)**

### **Daily Commands**
```powershell
# 1. Start development session
python scripts/validate_environment.py

# 2. Run specific tests (fast feedback)
python -m pytest tests/unit/test_model_adapter.py -v

# 3. Run all tests (comprehensive, ~5-10 min)
python -m pytest tests/ -v

# 4. Code quality check
ruff check src/ --fix
black src/
mypy src/

# 5. Pre-commit validation
pre-commit run --all-files
```

### **Making Changes**
```powershell
# ✅ DO: Use NEW structure
from src.openchronicle.domain import entities
from src.openchronicle.application import services

# ❌ DON'T: Use legacy imports (will break soon!)
from openchronicle.domain.models.model_orchestrator import ModelOrchestrator  # Modern architecture
from utilities.logging_system import log_event       # Moving to infrastructure
```

## 📊 **Key Metrics & Status**

### **Current Baselines**
- **Tests**: 347 total tests across unit/integration/workflows
- **Code Quality**: ruff, black, mypy, pre-commit all configured
- **Performance**: Baseline captured in `storage/performance_baseline.json`
- **Architecture**: Migration tracking in `.github/MIGRATION_TRACKING.md`

### **Development Environment**
- **Python**: 3.12.4+ required
- **Quality Tools**: All configured and validated
- **CI/CD**: GitHub Actions with comprehensive testing
- **Documentation**: Comprehensive tracking system in place

## 🎯 **Common Tasks**

### **Adding New Features**
```powershell
# 1. Choose correct layer
#    Domain: Business rules, entities
#    Application: Orchestration, workflows
#    Infrastructure: External integrations
#    Interface: User interactions

# 2. Create in NEW structure
mkdir -p src/openchronicle/domain/new_feature
touch src/openchronicle/domain/new_feature/__init__.py

# 3. Write tests first
touch tests/unit/domain/test_new_feature.py

# 4. Implement with proper imports
# Use: from src.openchronicle.domain import ...
```

### **Working with Models**
```powershell
# ✅ CURRENT: Use ModelOrchestrator through core/
from openchronicle.application.orchestrators.model_orchestrator import ModelOrchestrator

# 🎯 FUTURE: Will become hexagonal structure
from src.openchronicle.application.services.model_service import ModelService
```

### **Testing Patterns**
```powershell
# Unit tests (fast)
python -m pytest tests/unit/ -v

# Integration tests (slower)
python -m pytest tests/integration/ -v

# Specific feature
python -m pytest tests/ -k "model_adapter" -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## ⚠️ **Phase 1 Breaking Changes Alert**

**ACTIVE NOW**: Phase 1 import cleanup will break existing imports!

### **What's Changing**
- All `core.*` imports will be removed/redirected
- `utilities.*` imports moving to `src.openchronicle.infrastructure.*`
- Deep relative imports (`from ....foo import bar`) will break

### **Migration Strategy**
1. **Check current status**: See `MIGRATION_PROGRESS_BOARD.md`
2. **Update imports proactively**: Use new `src.openchronicle.*` structure
3. **Run import analysis**: `python scripts/import_analysis.py`
4. **Daily team sync**: Coordinate breaking changes

## 🆘 **Getting Help**

### **Quick Debugging**
```powershell
# Environment issues
python scripts/validate_environment.py

# Import problems
python scripts/import_analysis.py

# Test failures
python -m pytest tests/ -v --tb=short

# Performance concerns
python scripts/performance_baseline.py
```

### **Documentation**
- **Architecture**: `docs/ARCHITECTURE.md`
- **Migration Tracking**: `.github/MIGRATION_TRACKING.md`
- **Progress Board**: `MIGRATION_PROGRESS_BOARD.md`
- **Development**: `CONTRIBUTING.md`

### **Key Files**
```
🔍 Essential files to know:
├── main.py                           # Application entry point
├── src/openchronicle/__init__.py     # NEW package root
├── core/model_management/            # LEGACY model orchestration
├── tests/conftest.py                 # Test configuration
└── scripts/validate_environment.py  # Development validation
```

## 🎉 **You're Ready!**

**Next Steps:**
1. ✅ Run `python scripts/validate_environment.py`
2. ✅ Check `MIGRATION_PROGRESS_BOARD.md` for current status
3. ✅ Run `python -m pytest tests/unit/ -v` for quick validation
4. ✅ Start coding with NEW `src.openchronicle.*` imports

**Questions?** Check the documentation files or run the analysis scripts!

---
*Generated: Phase 0 completion - OpenChronicle ready for hexagonal architecture migration*

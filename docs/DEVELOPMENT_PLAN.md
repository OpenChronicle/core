# OpenChronicle Development Plan

**Version**: 1.0  
**Updated**: August 9, 2025  
**Status**: Active - Phase 0 Ready  

## 1. Scope & Non-Goals

### In Scope
- **Architecture Migration**: Complete dual → single hexagonal architecture
- **Documentation Standardization**: Unified, current, minimal documentation
- **Security Hardening**: Comprehensive scanning and validation
- **Type Safety**: Full mypy strict compliance
- **Test Excellence**: Maintain 85%+ coverage during migration

### Non-Goals
- **Feature Development**: Focus on architecture, not new features
- **Performance Optimization**: Current performance is acceptable
- **UI/UX Changes**: Existing interfaces work well
- **Backward Compatibility**: Internal project allows breaking changes

## 2. Architecture at a Glance

```
Current State (DUAL):
├── core/                    # Legacy monolithic modules
└── src/openchronicle/       # Modern hexagonal architecture

Target State (UNIFIED):
src/openchronicle/
├── domain/                  # Core business logic
├── application/             # Use cases and orchestration  
├── infrastructure/          # External service adapters
├── interfaces/              # User-facing adapters
└── shared/                  # Cross-cutting concerns
```

**Key Systems**: 13 orchestrator modules, 15+ LLM adapters, 404/418 tests passing (96.7%)

## 3. Milestones & Workstreams

| Milestone | Owner | DoD | ETA | Status |
|-----------|-------|-----|-----|--------|
| **Phase 0: Foundation** | Team | Security tools, docs framework, logging | Aug 11 | Ready |
| **Phase 1: Legacy Migration** | Team | Zero `core/` imports, unified structure | Aug 25 | Planned |
| **Phase 2: Structure Cleanup** | Team | Clean boundaries, consistent naming | Sep 1 | Planned |
| **Phase 3: Testing & Typing** | Team | 85%+ coverage, strict mypy | Sep 8 | Planned |
| **Phase 4: CI/CD Enhancement** | Team | Security pipeline, automation | Sep 15 | Planned |

## 4. Coding Standards

- **Style**: [ruff](pyproject.toml) + [black](pyproject.toml) + [isort](pyproject.toml)
- **Typing**: mypy strict mode, no `Any` without justification
- **Imports**: Absolute only (`from openchronicle.domain import...`)
- **Docstrings**: Google style, Args/Returns/Raises for public APIs
- **Testing**: pytest, 85% coverage minimum

## 5. Testing Strategy & Coverage Target

- **Target**: 85% minimum coverage (currently 96.7%)
- **Structure**: `tests/` mirrors `src/` exactly
- **Types**: unit, integration, e2e in separate directories
- **Fixtures**: Centralized in `tests/conftest.py`
- **Mocking**: Professional mock system for external dependencies

## 6. Release & Versioning Policy

- **Scheme**: Semantic versioning (0.1.x → 0.2.0 → 1.0.0)
- **Branches**: `main` for releases, feature branches for development
- **CI/CD**: Automated testing, manual release approval
- **Breaking Changes**: Allowed and encouraged for better architecture

## 7. Operational Notes

- **Logging**: Centralized via `shared/logging.py`, structured format
- **Config**: pydantic-settings with `.env` support
- **Errors**: Custom exception hierarchy in `shared/exceptions.py`
- **Health**: Test suite execution as primary health indicator

## 8. Open Risks & Decisions

### Current Risks
1. **R1**: Dual architecture maintenance burden → *Phase 1 migration*
2. **R2**: Import confusion during transition → *Automated tooling*

### Architecture Decisions
- **ADR-001**: Hexagonal architecture adoption → See `docs/adr/0001-hexagonal-architecture.md`
- **ADR-002**: Legacy migration strategy → See `docs/adr/0002-legacy-migration.md`

## How to Contribute Today

### Quick Start
1. **Setup**: `pip install -e ".[dev]"` + `pre-commit install`
2. **Test**: `pytest --cov=src --cov-fail-under=85`
3. **Lint**: `ruff check . && black --check . && mypy .`

### Phase 0 Tasks (Ready Now)
- [ ] Add security dependencies to pyproject.toml
- [ ] Enhance pre-commit hooks
- [ ] Create CONTRIBUTING.md
- [ ] Implement centralized logging
- [ ] Run baseline analysis

### Development Workflow
1. Create feature branch from `main`
2. Make changes following coding standards
3. Run full test suite (`make test`)
4. Submit PR with clear description
5. Address review feedback
6. Merge after approval

---

**Next Steps**: Execute Phase 0 foundation hardening immediately. See `.copilot/PHASE_0_DETAILED_TASKS.md` for specific tasks.

**Questions?** Check `.copilot/project_status.json` for current status or `.copilot/ARCHITECTURAL_MIGRATION_PHASES.md` for detailed migration plan.

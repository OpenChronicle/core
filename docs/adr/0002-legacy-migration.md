# ADR-002: Legacy Migration Strategy

**Status**: Accepted  
**Date**: 2025-08-09  
**Deciders**: OpenChronicle Team  

## Context

### Problem Statement
The codebase currently has dual architecture:
- Legacy `core/` modules with monolithic structure
- Modern `src/openchronicle/` hexagonal architecture

This creates:
- Import confusion (`from core` vs `from openchronicle`)
- Maintenance burden on two codebases
- Unclear ownership boundaries
- Risk of circular dependencies

### Constraints
- Must preserve all existing functionality
- Cannot break current test suite (404/418 passing)
- Must maintain development velocity during migration
- No backward compatibility requirements (internal project)

## Decision

### Chosen Approach
Phased migration approach with complete legacy elimination:

**Phase 1: Business Logic Migration**
- Migrate `core/models/` → `src/openchronicle/domain/models/`
- Migrate `core/analysis/` → `src/openchronicle/domain/services/`
- Update internal imports to absolute paths

**Phase 2: Application Services**
- Migrate `core/management/` → `src/openchronicle/application/services/`
- Implement CQRS pattern for commands and queries
- Update orchestration logic

**Phase 3: Infrastructure & Interfaces**
- Migrate adapters and external service integrations
- Update CLI and API interfaces
- Complete import path updates

**Phase 4: Complete Legacy Removal**
- Delete entire `core/` directory
- Update all references and documentation
- Verify no legacy imports remain

### Alternatives Considered
- **Gradual Refactoring**: Rejected due to indefinite dual maintenance
- **Big Bang Migration**: Rejected due to high risk and complexity
- **Wrapper Layer**: Rejected as it adds complexity without benefit

## Consequences

### Positive
- Single source of truth for architecture
- Eliminates import confusion
- Reduces maintenance burden
- Cleaner dependency relationships
- Enables full hexagonal architecture benefits

### Negative
- Significant migration effort (1-2 weeks)
- Risk of introducing bugs during migration
- Temporary import changes during transition
- All team members must update their knowledge

### Neutral
- Different import patterns required
- File locations change
- Need to update development tools/scripts

## Implementation

### Action Items
- [ ] **Phase 0**: Foundation hardening (security, docs, logging)
- [ ] **Phase 1**: Migrate core business logic (3-4 days)
- [ ] **Phase 2**: Migrate application services (2-3 days)  
- [ ] **Phase 3**: Migrate infrastructure & interfaces (2-3 days)
- [ ] **Phase 4**: Remove legacy code entirely (1 day)

### Validation
- Zero `from core` imports remaining in codebase
- All tests pass with new architecture
- No functionality regression
- Performance benchmarks maintained
- Documentation updated to reflect new structure

### Success Criteria
- Single architecture: only `src/openchronicle/` exists
- Clean dependency layers enforced
- 85%+ test coverage maintained
- Zero legacy technical debt

## References

- Migration plan details: `.copilot/ARCHITECTURAL_MIGRATION_PHASES.md`
- Phase 0 tasks: `.copilot/PHASE_0_DETAILED_TASKS.md`
- Current status: `.copilot/project_status.json`
- Development philosophy: `.copilot/DEVELOPMENT_PHILOSOPHY.md`

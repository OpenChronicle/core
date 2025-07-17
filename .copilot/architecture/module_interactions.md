# OpenChronicle Architecture Overview

## Core Module Interactions

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   story_loader  │    │ context_builder │    │  model_adapter  │
│                 │    │                 │    │                 │
│ • Load meta.yaml│───▶│ • Build prompts │───▶│ • LLM providers │
│ • Parse canon   │    │ • Inject style  │    │ • Fallback logic│
│ • Load chars    │    │ • Add memory    │    │ • Token limits  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ memory_manager  │    │ content_analyzer│    │  scene_logger   │
│                 │    │                 │    │                 │
│ • World state   │◀──▶│ • Classify tone │    │ • Log scenes    │
│ • Character mem │    │ • NSFW detect   │    │ • Memory snaps  │
│ • Flags/events  │    │ • Smart routing │    │ • Rollback pts  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │    database     │
                    │                 │
                    │ • SQLite per    │
                    │   story         │
                    │ • Rollback      │
                    │   support       │
                    └─────────────────┘
```

## Data Flow Patterns

### 1. Scene Generation Flow
```
User Input → content_analyzer → memory_manager → context_builder → model_adapter → scene_logger
```

### 2. Memory Update Flow
```
Scene Output → content_analyzer → memory_manager → database
```

### 3. Rollback Flow
```
User Request → rollback_engine → database → memory_manager → scene_logger
```

## Module Responsibilities

### Core Processing Modules
- **story_loader**: Static content loading and validation
- **context_builder**: Dynamic prompt construction
- **model_adapter**: LLM interaction and fallback handling
- **content_analyzer**: Content classification and routing
- **memory_manager**: State persistence and retrieval
- **scene_logger**: Scene persistence and rollback points
- **rollback_engine**: Time travel and state restoration
- **database**: SQLite operations and migrations

### Integration Points
- All modules use `DatabaseManager` for consistent SQLite access
- All modules use `utilities.logging_system` for centralized logging
- Configuration loaded via `story_loader` and shared across modules
- Memory state synchronized between `memory_manager` and `scene_logger`

## Design Patterns Used

### 1. Factory Pattern
- `ModelAdapter` creates provider-specific clients
- `DatabaseManager` creates story-specific connections

### 2. Strategy Pattern
- Content analysis strategies for different content types
- Model selection strategies based on content classification

### 3. Observer Pattern
- Memory updates trigger scene logging
- Content analysis results trigger model routing

### 4. Chain of Responsibility
- Model fallback chains
- Content analysis pipeline

## Error Handling Strategy

### Module-Level Errors
- Each module handles its own errors
- Graceful degradation when possible
- Detailed logging for debugging

### System-Level Errors
- Database corruption → rollback to last valid state
- Model failure → fallback to next in chain
- Memory corruption → rebuild from scene history

## Performance Considerations

### Database
- SQLite per story (isolation)
- Indexes on frequently queried fields
- Batch operations for bulk updates

### Memory
- LRU caching for frequently accessed data
- Lazy loading of large content
- Garbage collection of old scenes

### LLM Integration
- Token optimization via content analysis
- Request batching where possible
- Async operations for non-blocking calls

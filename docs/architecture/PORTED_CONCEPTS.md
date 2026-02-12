# Ported Concepts (Reference Only)

Concepts reviewed from v1 and reinterpreted in v2:

- Model orchestration patterns from `v1.reference/src/openchronicle/domain/models/model_orchestrator.py` informed the new `OrchestratorService` separation of response generation and lifecycle.
- Dynamic registry/adapter discovery ideas from `v1.reference/src/openchronicle/infrastructure/registry/registry_manager.py` shaped the plugin loader and adapter indirection.
- Centralized logging with contextual metadata in `v1.reference/src/openchronicle/shared/logging_system.py` inspired the dedicated `EventLogger` and hash-chained events.
- Persistence orchestration in `v1.reference/src/openchronicle/infrastructure/persistence/database_orchestrator.py` influenced the `SqliteStore` abstraction and schema bootstrap.
- Plugin wiring patterns from `v1.reference/src/openchronicle/plugins/storytelling/plugin.py` guided the simplified `register(registry)` contract.

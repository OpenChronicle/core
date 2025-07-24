# OpenChronicle Copilot Instructions

## Architecture Overview
OpenChronicle is a narrative AI engine with **13 core modules** using plugin-style model management. The `ModelManager` (`core/model_adapter.py`) orchestrates 15+ LLM providers with fallback chains and dynamic configuration loading.

**Critical Pattern**: Always route through `ModelManager` - never instantiate adapters directly.

## Core Development Workflows

### Model Adapter Usage
```python
# Check adapter exists before using
if adapter_name not in model_manager.adapters:
    await model_manager.initialize_adapter(adapter_name)

# Use fallback chains for resilience  
chain = model_manager.get_fallback_chain(adapter_name)
for attempt_adapter in chain:
    try:
        response = await adapter.generate_response(prompt)
        break
    except Exception:
        continue
```

### Configuration Pattern
- **Primary**: `config/model_registry.json` (registry-only, single source of truth)
- **Dynamic**: Use `model_manager.add_model_config()` for runtime additions

### Memory-Scene Synchronization 
```python
# ALWAYS update memory before logging scenes
memory_manager.update_character_memory(story_id, character_updates)
scene_logger.save_scene(story_id, scene_data, memory_snapshot)
```

## Testing & Development Commands
```bash
# Quick validation
python -c "from core.model_adapter import ModelManager; print('OK')"

# Test with mocks only
python main.py --test --max-iterations 1

# Specific module testing
python -m pytest tests/test_model_adapter.py::test_dynamic_model_management -v
```

## Docker Development
- **Init Pattern**: `/usr/local/bin/init-app.sh` copies `/app-template/` → `/app/` on first run
- **Volume**: External mount `/volume1/docker/openchronicle:/app` for persistence
- **Network**: `ollama_openchronicle` external network with ollama-alpha:11434

## Project-Specific Conventions
- **Logging**: Import from `utilities/logging_system`, use `log_system_event(type, description)`
- **Transformers**: Check `TRANSFORMERS_AVAILABLE` before import (graceful fallback)
- **Async**: All model operations use async/await patterns with proper exception handling
- **PowerShell**: Use semicolons (`;`) not `&&` for command chaining

## Key Architecture Files
- `core/model_adapter.py` - Central orchestration (1500+ lines)
- `.copilot/architecture/module_interactions.md` - System design
- `tests/test_model_adapter.py` - Testing patterns and mocking

# Plugin contract

## Core promises

- Plugin loader discovers packages under plugins/ with **init**.py and plugin.py.
- Handlers are registered by task type using the TaskHandlerRegistry.
- Handler naming follows the pattern namespace.action (for example, hello.echo).
- Execution is deterministic for identical inputs unless explicitly stated.
- Core selftests require no external network calls or API keys.
- Events record task lifecycle and plugin handler start/finish but do not record raw prompts or tokens.

## Plugin promises

- Provide metadata fields:
  - id
  - name
  - version
  - entrypoint
  - expose these as module-level constants in plugin.py (PLUGIN_ID, PLUGIN_NAME, PLUGIN_VERSION, PLUGIN_ENTRYPOINT)
- Deterministic output for the same inputs.
- Do not log or emit secrets, prompts, or tokens in plain text.
- Must not import from v1.reference at runtime.

## Testing expectations

- Run local tests:

```bash
python -m pytest
```

- Run Docker acceptance:

```powershell
pwsh tools/docker/acceptance.ps1
```

- Run plugin-in-docker harness:

```powershell
pwsh tools/plugin_dev/run_plugin_in_docker.ps1 -PluginDir .\plugins
```

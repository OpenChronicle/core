# Plugin quickstart

## Structure

Plugins live under the top-level plugins/ directory. Each plugin must be a package with **init**.py and a plugin.py entrypoint:

```text
plugins/
  hello_plugin/
    __init__.py
    plugin.py
```

## Entry point

Implement a register() function in plugin.py that receives the PluginRegistry and TaskHandlerRegistry:

- register a task handler with a deterministic task type
- avoid external dependencies

## Run locally

```bash
python -m pytest
```

```bash
oc selftest --json
```

## Run in Docker

```bash
docker build -t openchronicle-core:local .
```

```bash
docker run --rm openchronicle-core:local selftest --json
```

## Invoke the hello plugin

Use the normal task path (orchestrator/run-task) with task type hello.echo:

```bash
oc run-task <project_id> hello.echo '{"prompt":"hello"}'
```

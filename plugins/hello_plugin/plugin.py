from __future__ import annotations

from typing import Any

from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
from openchronicle.core.domain.models.project import Task
from openchronicle.core.domain.ports.plugin_port import PluginRegistry

PLUGIN_ID = "hello"
PLUGIN_NAME = "Hello Plugin"
PLUGIN_VERSION = "1.0.0"
PLUGIN_ENTRYPOINT = "plugins/hello_plugin/plugin.py"


async def _hello_echo_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, str]:
    payload = task.payload or {}
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    text = prompt if isinstance(prompt, str) and prompt else "hello"
    return {"echo": text}


def register(
    registry: PluginRegistry,
    handler_registry: TaskHandlerRegistry,
    context: dict[str, Any] | None = None,
) -> None:
    handler_registry.register("hello.echo", _hello_echo_handler)
    registry.register_agent_template({"role": "hello", "description": "Echoes a prompt."})

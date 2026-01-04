from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from openchronicle_core.core.domain.ports.plugin_port import PluginRegistry, TaskHandler


class InMemoryPluginRegistry(PluginRegistry):
    def __init__(self) -> None:
        self._task_handlers: dict[str, TaskHandler] = {}
        self._agent_templates: list[dict] = []

    def register_task_handler(self, task_type: str, handler: TaskHandler) -> None:
        self._task_handlers[task_type] = handler

    def get_task_handler(self, task_type: str) -> TaskHandler | None:
        return self._task_handlers.get(task_type)

    def register_agent_template(self, agent: dict) -> None:
        self._agent_templates.append(agent)

    def list_agent_templates(self) -> list[dict]:
        return list(self._agent_templates)


class PluginLoader:
    def __init__(self, plugins_dir: str = "plugins") -> None:
        self.plugins_dir = Path(plugins_dir)
        self.registry = InMemoryPluginRegistry()

    def load_plugins(self) -> None:
        if not self.plugins_dir.exists():
            return
        for module_info in pkgutil.iter_modules([str(self.plugins_dir)]):
            if module_info.ispkg:
                module_name = f"plugins.{module_info.name}.plugin"
                try:
                    module = importlib.import_module(module_name)
                except Exception:
                    continue
                if hasattr(module, "register"):
                    try:
                        module.register(self.registry)
                    except Exception:
                        # Do not crash core if plugin fails
                        continue

    def registry_instance(self) -> PluginRegistry:
        return self.registry

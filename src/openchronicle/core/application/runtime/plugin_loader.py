from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from openchronicle.core.application.runtime.task_handler_registry import TaskHandlerRegistry
from openchronicle.core.domain.ports.plugin_port import PluginRegistry, TaskHandler


class InMemoryPluginRegistry(PluginRegistry):
    def __init__(self) -> None:
        self._task_handlers: dict[str, TaskHandler] = {}
        self._agent_templates: list[dict[str, Any]] = []

    def register_task_handler(self, task_type: str, handler: TaskHandler) -> None:
        self._task_handlers[task_type] = handler

    def get_task_handler(self, task_type: str) -> TaskHandler | None:
        return self._task_handlers.get(task_type)

    def register_agent_template(self, agent: dict[str, Any]) -> None:
        self._agent_templates.append(agent)

    def list_agent_templates(self) -> list[dict[str, Any]]:
        return list(self._agent_templates)


class PluginLoader:
    def __init__(self, plugins_dir: str = "plugins", handler_registry: TaskHandlerRegistry | None = None) -> None:
        self.plugins_dir = Path(plugins_dir)
        self.registry = InMemoryPluginRegistry()
        self.handler_registry = handler_registry or TaskHandlerRegistry()

    def _find_repo_root(self) -> Path:
        """Find repository root by walking up until pyproject.toml is found."""
        current = Path(__file__).resolve()
        for parent in [current] + list(current.parents):
            if (parent / "pyproject.toml").exists():
                return parent
        # Fallback: assume plugins_dir parent if pyproject.toml not found
        return self.plugins_dir.resolve().parent

    def load_plugins(self, context: dict[str, Any] | None = None) -> None:
        """Load plugins from filesystem by file path (no sys.path manipulation)."""
        repo_root = self._find_repo_root()
        plugins_root = repo_root / self.plugins_dir

        if not plugins_root.exists():
            return

        # Discover plugin candidates: directories under plugins/ with plugin.py
        for plugin_dir in plugins_root.iterdir():
            if not plugin_dir.is_dir():
                continue

            plugin_file = plugin_dir / "plugin.py"
            if not plugin_file.exists():
                continue

            plugin_name = plugin_dir.name
            self._load_plugin(plugin_name, plugin_file, context)

    def _load_plugin(self, plugin_name: str, plugin_file: Path, context: dict[str, Any] | None) -> None:
        """Load a single plugin by file path using importlib.util."""
        # Use unique module name to avoid collisions
        module_name = f"oc_plugin_{plugin_name}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                print(f"Failed to create spec for plugin {plugin_name} at {plugin_file}", file=sys.stderr)
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        except Exception as exc:
            print(f"Failed to load plugin {plugin_name} from {plugin_file}: {exc}", file=sys.stderr)
            return

        # Call register function if it exists
        if not hasattr(module, "register"):
            print(
                f"Plugin {plugin_name} at {plugin_file} does not have a register() function",
                file=sys.stderr,
            )
            return

        try:
            module.register(self.registry, self.handler_registry, context)
        except Exception as exc:
            print(f"Failed to register plugin {plugin_name}: {exc}", file=sys.stderr)

    def registry_instance(self) -> PluginRegistry:
        return self.registry

    def handler_registry_instance(self) -> TaskHandlerRegistry:
        return self.handler_registry

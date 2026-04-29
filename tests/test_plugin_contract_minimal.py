from __future__ import annotations

import sys

from openchronicle.core.application.runtime.plugin_loader import PluginLoader
from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry


def test_plugin_contract_minimal() -> None:
    registry = TaskHandlerRegistry()
    loader = PluginLoader(plugins_dir="plugins", handler_registry=registry)
    loader.load_plugins()

    plugin_module = sys.modules.get("oc_plugins.storytelling.plugin")
    assert plugin_module is not None

    assert getattr(plugin_module, "PLUGIN_ID", None)
    assert getattr(plugin_module, "PLUGIN_NAME", None)
    assert getattr(plugin_module, "PLUGIN_VERSION", None)
    assert getattr(plugin_module, "PLUGIN_ENTRYPOINT", None)

    assert registry.get("story.draft") is not None

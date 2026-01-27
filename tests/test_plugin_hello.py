from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

import pytest

from openchronicle.core.application.runtime.plugin_loader import PluginLoader
from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
from openchronicle.core.application.services.orchestrator import OrchestratorService
from openchronicle.core.domain.models.project import TaskStatus
from openchronicle.core.infrastructure.llm.stub_adapter import StubLLMAdapter
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


def _copy_hello_plugin(tmp_path: Path) -> Path:
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "plugins" / "hello_plugin"
    shutil.copytree(source, plugins_dir / "hello_plugin")
    return plugins_dir


@pytest.mark.asyncio
async def test_hello_plugin_routes_via_orchestrator(tmp_path: Path) -> None:
    plugins_dir = _copy_hello_plugin(tmp_path)
    db_path = tmp_path / "hello.db"

    storage = SqliteStore(str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)

    handler_registry = TaskHandlerRegistry()
    plugin_loader = PluginLoader(plugins_dir=str(plugins_dir), handler_registry=handler_registry)
    plugin_loader.load_plugins()

    orchestrator = OrchestratorService(
        storage=storage,
        llm=StubLLMAdapter(),
        plugins=plugin_loader.registry_instance(),
        handler_registry=plugin_loader.handler_registry_instance(),
        emit_event=event_logger.append,
    )

    project = orchestrator.create_project("Hello")
    task = orchestrator.submit_task(project.id, "hello.echo", {"prompt": "hi"})
    result = await orchestrator.execute_task(task.id)
    result_payload = cast(dict[str, str], result)
    assert result_payload == {"echo": "hi"}

    stored_task = storage.get_task(task.id)
    assert stored_task is not None
    assert stored_task.status == TaskStatus.COMPLETED

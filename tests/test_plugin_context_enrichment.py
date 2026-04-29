"""Tests for enriched plugin handler context.

Verifies that plugin handlers receive memory operations, LLM access,
and plugin config in their context dict — all pre-bound so plugins
never touch ports or services directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from openchronicle.core.application.runtime.plugin_loader import PluginLoader
from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
from openchronicle.core.application.services.embedding_service import EmbeddingService
from openchronicle.core.application.services.orchestrator import OrchestratorService
from openchronicle.core.domain.models.project import Task, TaskStatus
from openchronicle.core.domain.ports.embedding_port import EmbeddingPort
from openchronicle.core.domain.ports.llm_port import LLMPort, LLMResponse
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeLLM(LLMPort):
    """Deterministic LLM that echoes input for testing."""

    async def complete_async(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        content = " ".join(m.get("content", "") for m in messages)
        return LLMResponse(content=f"llm:{content}", provider=provider or "fake", model=model)


class StubEmbeddingPort(EmbeddingPort):
    """Stub that returns zero vectors."""

    def embed(self, text: str) -> list[float]:
        return [0.0] * 8

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 8 for _ in texts]

    def dimensions(self) -> int:
        return 8

    def model_name(self) -> str:
        return "stub-embedding"


# ---------------------------------------------------------------------------
# Handler that captures its context for assertions
# ---------------------------------------------------------------------------

_captured_context: dict[str, Any] = {}


async def _capture_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, str]:
    _captured_context.clear()
    _captured_context.update(context or {})
    return {"status": "captured"}


async def _memory_round_trip_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Handler that exercises memory_save + memory_search."""
    ctx = context or {}
    saved = ctx["memory_save"]("test content from plugin", tags=["test-tag"])
    results = ctx["memory_search"]("test content", top_k=5)
    return {"saved_id": saved.id, "search_count": len(results)}


async def _llm_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Handler that exercises llm_complete."""
    ctx = context or {}
    response = await ctx["llm_complete"]([{"role": "user", "content": "ping"}])
    return {"llm_content": response.content, "llm_provider": response.provider}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _setup(tmp_path: Path) -> dict[str, Any]:
    """Shared test infrastructure: storage, orchestrator, project."""
    db_path = tmp_path / "test.db"
    storage = SqliteStore(db_path=str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)

    embedding_port = StubEmbeddingPort()
    embedding_service = EmbeddingService(embedding_port, storage)

    handler_registry = TaskHandlerRegistry()
    handler_registry.set_current_source("test_plugin")
    handler_registry.register("test.capture", _capture_handler)
    handler_registry.register("test.memory_round_trip", _memory_round_trip_handler)
    handler_registry.register("test.llm", _llm_handler)
    handler_registry.set_current_source(None)

    plugin_configs = {"test_plugin": {"api_url": "http://localhost:9999", "token": "abc"}}

    orchestrator = OrchestratorService(
        storage=storage,
        llm=FakeLLM(),
        plugins=PluginLoader(plugins_dir="plugins").registry_instance(),
        handler_registry=handler_registry,
        emit_event=event_logger.append,
        embedding_service=embedding_service,
        plugin_configs=plugin_configs,
    )

    project = orchestrator.create_project("TestProject")
    return {
        "storage": storage,
        "orchestrator": orchestrator,
        "project": project,
        "handler_registry": handler_registry,
        "embedding_service": embedding_service,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handler_receives_all_enriched_context_keys(_setup: dict[str, Any]) -> None:
    """Handler context includes all base + enriched keys."""
    orch = _setup["orchestrator"]
    project = _setup["project"]

    task = orch.submit_task(project.id, "test.capture", {})
    await orch.execute_task(task.id)

    expected_keys = {
        "agent_id",
        "attempt_id",
        "emit_event",
        "memory_save",
        "memory_search",
        "memory_update",
        "llm_complete",
        "plugin_config",
    }
    assert expected_keys == set(_captured_context.keys())


@pytest.mark.asyncio
async def test_memory_save_persists_and_searchable(_setup: dict[str, Any]) -> None:
    """memory_save creates a MemoryItem retrievable via memory_search."""
    orch = _setup["orchestrator"]
    project = _setup["project"]

    task = orch.submit_task(project.id, "test.memory_round_trip", {})
    result = await orch.execute_task(task.id)

    assert result["saved_id"]  # non-empty
    assert result["search_count"] >= 1


@pytest.mark.asyncio
async def test_memory_save_auto_injects_project_id(_setup: dict[str, Any]) -> None:
    """memory_save auto-injects project_id from the task."""
    orch = _setup["orchestrator"]
    storage = _setup["storage"]
    project = _setup["project"]

    task = orch.submit_task(project.id, "test.memory_round_trip", {})
    await orch.execute_task(task.id)

    # Retrieve the saved memory directly from storage
    from openchronicle.core.application.use_cases import search_memory as search_uc

    memories = search_uc.execute(storage, "test content", project_id=project.id)
    assert len(memories) >= 1
    assert memories[0].project_id == project.id
    assert memories[0].source == "plugin"


@pytest.mark.asyncio
async def test_memory_update_modifies_existing(_setup: dict[str, Any]) -> None:
    """memory_update can modify content of an existing memory."""
    orch = _setup["orchestrator"]
    project = _setup["project"]

    # First, save a memory
    task1 = orch.submit_task(project.id, "test.capture", {})
    await orch.execute_task(task1.id)

    # Use the captured context to save + update
    saved = _captured_context["memory_save"]("original content", tags=["v1"])
    updated = _captured_context["memory_update"](saved.id, content="updated content", tags=["v2"])

    assert updated.content == "updated content"
    assert updated.tags == ["v2"]


@pytest.mark.asyncio
async def test_llm_complete_routes_through_fake_llm(_setup: dict[str, Any]) -> None:
    """llm_complete routes through the LLM port and returns LLMResponse."""
    orch = _setup["orchestrator"]
    project = _setup["project"]

    task = orch.submit_task(project.id, "test.llm", {})
    result = await orch.execute_task(task.id)

    assert result["llm_content"].startswith("llm:")
    assert "ping" in result["llm_content"]


@pytest.mark.asyncio
async def test_plugin_config_matches_configured_content(_setup: dict[str, Any]) -> None:
    """plugin_config contains the config dict for the handler's plugin."""
    orch = _setup["orchestrator"]
    project = _setup["project"]

    task = orch.submit_task(project.id, "test.capture", {})
    await orch.execute_task(task.id)

    assert _captured_context["plugin_config"] == {"api_url": "http://localhost:9999", "token": "abc"}


@pytest.mark.asyncio
async def test_existing_plugins_still_work(tmp_path: Path) -> None:
    """storytelling plugin works unchanged with enriched context."""
    db_path = tmp_path / "test.db"
    storage = SqliteStore(db_path=str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)

    handler_registry = TaskHandlerRegistry()
    plugin_loader = PluginLoader(plugins_dir="plugins", handler_registry=handler_registry)
    plugin_loader.load_plugins()

    orchestrator = OrchestratorService(
        storage=storage,
        llm=FakeLLM(),
        plugins=plugin_loader.registry_instance(),
        handler_registry=plugin_loader.handler_registry_instance(),
        emit_event=event_logger.append,
    )

    project = orchestrator.create_project("Test")

    task = orchestrator.submit_task(project.id, "story.draft", {"prompt": "Once"})
    result = await orchestrator.execute_task(task.id)
    assert result == {"draft": "[storytelling draft] Once"}
    assert storage.get_task(task.id).status == TaskStatus.COMPLETED  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_handler_without_plugin_config_gets_empty_dict(tmp_path: Path) -> None:
    """A handler with no matching plugin config receives empty dict."""
    db_path = tmp_path / "test.db"
    storage = SqliteStore(db_path=str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)

    handler_registry = TaskHandlerRegistry()
    # Register without setting a source — no plugin association
    handler_registry.register("orphan.handler", _capture_handler)

    orchestrator = OrchestratorService(
        storage=storage,
        llm=FakeLLM(),
        plugins=PluginLoader(plugins_dir="plugins").registry_instance(),
        handler_registry=handler_registry,
        emit_event=event_logger.append,
        plugin_configs={"some_other_plugin": {"key": "val"}},
    )

    project = orchestrator.create_project("Test")
    task = orchestrator.submit_task(project.id, "orphan.handler", {})
    await orchestrator.execute_task(task.id)

    assert _captured_context["plugin_config"] == {}


@pytest.mark.asyncio
async def test_memory_ops_work_without_embedding_service(tmp_path: Path) -> None:
    """Memory closures degrade gracefully to FTS5-only when no embedding service."""
    db_path = tmp_path / "test.db"
    storage = SqliteStore(db_path=str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)

    handler_registry = TaskHandlerRegistry()
    handler_registry.register("test.memory_round_trip", _memory_round_trip_handler)

    orchestrator = OrchestratorService(
        storage=storage,
        llm=FakeLLM(),
        plugins=PluginLoader(plugins_dir="plugins").registry_instance(),
        handler_registry=handler_registry,
        emit_event=event_logger.append,
        # No embedding_service — should still work via FTS5
    )

    project = orchestrator.create_project("Test")
    task = orchestrator.submit_task(project.id, "test.memory_round_trip", {})
    result = await orchestrator.execute_task(task.id)

    assert result["saved_id"]
    assert result["search_count"] >= 1

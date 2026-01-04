from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openchronicle_core.core.domain.models.project import Agent, Event, Project, Resource, Task, TaskStatus
from openchronicle_core.core.domain.ports.llm_port import LLMPort
from openchronicle_core.core.domain.ports.storage_port import StoragePort
from openchronicle_core.core.domain.ports.plugin_port import PluginRegistry


class OrchestratorService:
    def __init__(
        self,
        storage: StoragePort,
        llm: LLMPort,
        plugins: PluginRegistry,
        emit_event: Callable[[Event], None],
    ) -> None:
        self.storage = storage
        self.llm = llm
        self.plugins = plugins
        self.emit_event = emit_event

    def create_project(self, name: str, metadata: dict[str, Any] | None = None) -> Project:
        project = Project(name=name, metadata=metadata or {})
        self.storage.add_project(project)
        event = Event(project_id=project.id, type="project_created", payload={"name": name})
        event.compute_hash()
        self.emit_event(event)
        return project

    def register_agent(
        self,
        project_id: str,
        name: str,
        role: str = "worker",
        provider: str = "",
        model: str = "",
        tags: list[str] | None = None,
    ) -> Agent:
        agent = Agent(
            project_id=project_id,
            role=role,
            name=name,
            provider=provider,
            model=model,
            tags=tags or [],
        )
        self.storage.add_agent(agent)
        event = Event(project_id=project_id, agent_id=agent.id, type="agent_registered", payload={"name": name, "role": role})
        event.compute_hash()
        self.emit_event(event)
        return agent

    def submit_task(self, project_id: str, task_type: str, payload: dict[str, Any]) -> Task:
        task = Task(project_id=project_id, type=task_type, payload=payload)
        self.storage.add_task(task)
        event = Event(project_id=project_id, task_id=task.id, type="task_submitted", payload={"task_type": task_type})
        event.compute_hash()
        self.emit_event(event)
        return task

    async def execute_task(self, task_id: str, agent_id: str | None = None) -> str:
        task = self.storage.get_task(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        self.storage.update_task_status(task.id, TaskStatus.RUNNING.value)
        start_event = Event(project_id=task.project_id, task_id=task.id, agent_id=agent_id, type="task_started", payload={})
        start_event.compute_hash()
        self.emit_event(start_event)

        handler = self.plugins.get_task_handler(task.type)
        if handler is not None:
            result = await handler(task, context={"agent_id": agent_id})
        else:
            prompt = task.payload.get("prompt") or task.payload.get("text") or ""
            result = await self.llm.generate_async(prompt, model=None, parameters=None)

        complete_event = Event(project_id=task.project_id, task_id=task.id, agent_id=agent_id, type="task_completed", payload={"result": result})
        complete_event.compute_hash()
        self.emit_event(complete_event)
        self.storage.update_task_status(task.id, TaskStatus.COMPLETED.value)
        return result

    def record_resource(self, resource: Resource) -> None:
        self.storage.add_resource(resource)
        event = Event(project_id=resource.project_id, type="resource_added", payload={"kind": resource.kind, "path": resource.path})
        event.compute_hash()
        self.emit_event(event)

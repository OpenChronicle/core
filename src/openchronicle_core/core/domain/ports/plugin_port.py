from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Protocol

from openchronicle_core.core.domain.models.project import Task


class TaskHandler(Protocol):
    async def __call__(self, task: Task, *, context: dict | None = None) -> str: ...


class PluginRegistry(ABC):
    @abstractmethod
    def register_task_handler(self, task_type: str, handler: TaskHandler) -> None:
        ...

    @abstractmethod
    def get_task_handler(self, task_type: str) -> TaskHandler | None:
        ...

    @abstractmethod
    def register_agent_template(self, agent: dict) -> None:
        ...

    @abstractmethod
    def list_agent_templates(self) -> list[dict]:
        ...


class PluginPort(ABC):
    @abstractmethod
    def load_plugins(self) -> None:
        ...

    @abstractmethod
    def registry(self) -> PluginRegistry:
        ...

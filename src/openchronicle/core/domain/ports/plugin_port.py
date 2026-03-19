from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Protocol


class ModePromptBuilder(Protocol):
    """Callable that produces a custom system prompt for a conversation mode."""

    def __call__(
        self,
        prompt_text: str,
        *,
        memory_search: Callable[..., list[Any]],
        project_id: str | None = None,
    ) -> str: ...


class PluginRegistry(ABC):
    @abstractmethod
    def register_agent_template(self, agent: dict[str, Any]) -> None: ...

    @abstractmethod
    def list_agent_templates(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def register_mode_prompt_builder(self, mode: str, builder: ModePromptBuilder) -> None: ...

    @abstractmethod
    def get_mode_prompt_builder(self, mode: str) -> ModePromptBuilder | None: ...

    @abstractmethod
    def mode_prompt_builders(self) -> dict[str, ModePromptBuilder]: ...


class PluginPort(ABC):
    @abstractmethod
    def load_plugins(self) -> None: ...

    @abstractmethod
    def registry(self) -> PluginRegistry: ...

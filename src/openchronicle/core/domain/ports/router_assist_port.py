from __future__ import annotations

from typing import Protocol

from openchronicle.core.domain.models.assist_result import RouterAssistResult


class RouterAssistPort(Protocol):
    def analyze(self, text: str, mode_hint: str | None = None) -> RouterAssistResult: ...

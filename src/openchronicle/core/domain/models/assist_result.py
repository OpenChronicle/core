from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RouterAssistResult:
    nsfw_probability: float
    confidence: float
    reason_codes: list[str] = field(default_factory=list)
    backend: str = "linear"

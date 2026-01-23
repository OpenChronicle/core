from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PrivacyReport:
    categories: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    action: str = "off"
    redactions_applied: bool = False
    summary: str = ""

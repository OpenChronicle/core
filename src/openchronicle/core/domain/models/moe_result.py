"""Mixture-of-Experts execution result models."""

from __future__ import annotations

from dataclasses import dataclass, field

from openchronicle.core.domain.ports.llm_port import LLMUsage


@dataclass
class MoEExpertResult:
    """Result from a single expert in a MoE consensus run."""

    provider: str
    model: str
    content: str
    weight: int = 100
    consensus_score: float = 0.0
    latency_ms: int | None = None
    usage: LLMUsage | None = None
    error: str | None = None


@dataclass
class MoEResult:
    """Aggregated result from a MoE consensus run."""

    winner: MoEExpertResult
    experts: list[MoEExpertResult] = field(default_factory=list)
    agreement_ratio: float = 0.0

"""Mixture-of-Experts execution strategy.

Runs N experts in parallel, scores consensus via Jaccard similarity,
and returns the winner. V0 is non-streaming.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from openchronicle.core.application.routing.pool_config import ProviderCandidate
from openchronicle.core.application.routing.router_policy import RouteDecision
from openchronicle.core.application.services.llm_execution import execute_with_route
from openchronicle.core.domain.errors.error_codes import MOE_INSUFFICIENT_EXPERTS
from openchronicle.core.domain.models.moe_result import MoEExpertResult, MoEResult
from openchronicle.core.domain.ports.llm_port import LLMPort, LLMProviderError


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokenization. No external deps."""
    return set(re.findall(r"\w+", text.lower()))


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compute_consensus_scores(
    results: list[MoEExpertResult],
) -> list[MoEExpertResult]:
    """Mutate each result's consensus_score in-place. Return sorted desc.

    Score = avg Jaccard similarity to all other successful experts.
    Tiebreak: higher weight wins. Second tiebreak: earlier in list (stable sort).
    """
    if len(results) <= 1:
        for r in results:
            r.consensus_score = 1.0
        return results

    token_sets = [_tokenize(r.content) for r in results]

    for i, result in enumerate(results):
        similarities = []
        for j, _other in enumerate(results):
            if i != j:
                similarities.append(_jaccard_similarity(token_sets[i], token_sets[j]))
        result.consensus_score = sum(similarities) / len(similarities) if similarities else 0.0

    # Stable sort: highest consensus_score first, then highest weight
    results.sort(key=lambda r: (-r.consensus_score, -r.weight))
    return results


async def execute_moe(
    llm: LLMPort,
    candidates: list[ProviderCandidate],
    messages: list[dict[str, Any]],
    *,
    max_output_tokens: int | None = None,
    temperature: float | None = None,
    min_experts: int = 2,
) -> MoEResult:
    """Run N experts in parallel, score consensus, return winner.

    Raises LLMProviderError(error_code=MOE_INSUFFICIENT_EXPERTS) if
    fewer than min_experts succeed.
    """
    if len(candidates) < min_experts:
        raise LLMProviderError(
            f"MoE requires at least {min_experts} candidates, got {len(candidates)}",
            error_code=MOE_INSUFFICIENT_EXPERTS,
            hint=f"Configure at least {min_experts} providers in the quality pool.",
        )

    async def _call_expert(candidate: ProviderCandidate) -> MoEExpertResult:
        route = RouteDecision(
            provider=candidate.provider,
            model=candidate.model,
            mode="quality",
            reasons=[f"moe_expert:{candidate.provider}:{candidate.model}"],
        )
        started = time.perf_counter()
        try:
            response = await execute_with_route(
                llm,
                route,
                messages,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return MoEExpertResult(
                provider=candidate.provider,
                model=candidate.model,
                content="",
                weight=candidate.weight,
                latency_ms=elapsed_ms,
                error=str(exc),
            )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return MoEExpertResult(
            provider=candidate.provider,
            model=candidate.model,
            content=response.content,
            weight=candidate.weight,
            latency_ms=elapsed_ms,
            usage=response.usage,
        )

    # Run all experts in parallel
    all_results = await asyncio.gather(*[_call_expert(c) for c in candidates])
    all_experts = list(all_results)

    successful = [r for r in all_experts if r.error is None]

    if len(successful) < min_experts:
        failed_details = [f"{r.provider}:{r.model} -> {r.error}" for r in all_experts if r.error is not None]
        raise LLMProviderError(
            f"MoE: only {len(successful)} of {len(all_experts)} experts succeeded (min_experts={min_experts})",
            error_code=MOE_INSUFFICIENT_EXPERTS,
            hint="Check provider availability and credentials.",
            details={"failures": failed_details},
        )

    # Score consensus among successful experts
    scored = compute_consensus_scores(successful)

    # Compute agreement_ratio: average pairwise Jaccard among all successful
    token_sets = [_tokenize(r.content) for r in scored]
    pair_count = 0
    pair_sum = 0.0
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            pair_sum += _jaccard_similarity(token_sets[i], token_sets[j])
            pair_count += 1
    agreement_ratio = pair_sum / pair_count if pair_count > 0 else 1.0

    return MoEResult(
        winner=scored[0],
        experts=all_experts,
        agreement_ratio=agreement_ratio,
    )

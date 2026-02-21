"""Tests for the predictor seam on RouteDecision and explain output.

The predictor is NOT implemented — these tests lock in the no-op defaults
so that future work has a stable, auditable insertion point.
"""

from __future__ import annotations

import pytest

from openchronicle.core.application.routing.router_policy import RouteDecision, RouterPolicy


def test_route_decision_predictor_defaults() -> None:
    """RouteDecision predictor fields default to None."""
    decision = RouteDecision(
        provider="stub",
        model="stub-model",
        mode="fast",
        reasons=["test"],
    )
    assert decision.predictor_hint is None
    assert decision.predictor_source is None


def test_router_policy_route_returns_null_predictor(monkeypatch: pytest.MonkeyPatch) -> None:
    """RouterPolicy.route() never sets predictor fields today."""
    monkeypatch.setenv("OC_LLM_FAST_POOL", "")
    monkeypatch.setenv("OC_LLM_QUALITY_POOL", "")

    policy = RouterPolicy()
    decision = policy.route(
        task_type="test.task",
        agent_role="worker",
    )
    assert decision.predictor_hint is None
    assert decision.predictor_source is None

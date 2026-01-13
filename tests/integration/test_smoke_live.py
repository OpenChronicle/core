"""Integration tests for smoke_live use case.

These tests are opt-in and only run when required environment variables are present.
They test real provider integration (e.g., OpenAI, Ollama) when configured.

Marking these as integration tests so unit test suite stays keyless.
"""

from __future__ import annotations

import json
import os

import pytest

from openchronicle.core.application.runtime.container import CoreContainer
from openchronicle.core.application.use_cases import smoke_live

# Skip entire module unless integration test env var is set
pytestmark = pytest.mark.skipif(
    os.getenv("OC_INTEGRATION_TESTS") != "1",
    reason="Integration tests skipped unless OC_INTEGRATION_TESTS=1",
)


class TestSmokeLiveIntegration:
    """Integration tests for smoke_live use case with real providers."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup for each test."""
        # Container is created fresh for each test
        self.container = CoreContainer()
        self.orchestrator = self.container.orchestrator

    @pytest.mark.integration
    async def test_smoke_live_with_default_routing(self) -> None:
        """Test smoke_live with default routing (no provider override)."""
        # Use the default routing to select provider
        result = await smoke_live.execute(
            self.orchestrator,
            prompt="What is 2 + 2? Answer in one word.",
            provider=None,
            model=None,
        )

        # Assertions
        assert result.project_id is not None
        assert result.task_id is not None
        assert result.execution_id is not None
        assert result.attempt_id is not None
        assert result.provider_used is not None
        assert result.model_used is not None
        assert result.outcome == "completed", f"Expected outcome=completed, got {result.outcome}"
        # Tokens should be populated if provider supports it
        # (stub provider returns None, real providers return integers)
        # So we just check that if tokens are present, they're non-negative
        if result.total_tokens is not None:
            assert result.total_tokens > 0

    @pytest.mark.integration
    async def test_smoke_live_with_provider_override(self) -> None:
        """Test smoke_live with explicit provider override."""
        # Check if OpenAI is configured
        has_openai = os.getenv("OPENAI_API_KEY") is not None

        if not has_openai:
            pytest.skip("OpenAI not configured (no OPENAI_API_KEY)")

        result = await smoke_live.execute(
            self.orchestrator,
            prompt="Respond with: OK",
            provider="openai",
            model="gpt-4o-mini",
        )

        assert result.project_id is not None
        assert result.provider_requested == "openai"
        assert result.provider_used == "openai"
        assert result.model_requested == "gpt-4o-mini"
        assert result.model_used == "gpt-4o-mini"
        assert result.outcome == "completed"

    @pytest.mark.integration
    async def test_smoke_live_missing_credentials_error(self) -> None:
        """Test that missing credentials raise clear errors (no secrets leaked)."""
        # Force a provider that is not configured
        # Save original env var if present
        original_key = os.environ.pop("OPENAI_API_KEY", None)

        try:
            result = await smoke_live.execute(
                self.orchestrator,
                prompt="test",
                provider="openai",
                model="gpt-4o-mini",
            )

            # Should get a "blocked" or "failed" outcome with error_code
            assert result.outcome in ("blocked", "failed")
            assert result.error_code is not None
            # Ensure no secrets are in error message
            if result.error_message:
                assert "api_key" not in result.error_message.lower()
                assert "OPENAI" not in result.error_message  # (but "OpenAI" is ok)
        finally:
            # Restore original env var
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key

    @pytest.mark.integration
    async def test_smoke_live_with_custom_prompt(self) -> None:
        """Test smoke_live with custom prompt."""
        custom_prompt = "This is a custom test prompt for smoke testing."

        result = await smoke_live.execute(
            self.orchestrator,
            prompt=custom_prompt,
            provider=None,
            model=None,
        )

        assert result.project_id is not None
        assert result.prompt_text == custom_prompt
        # Outcome depends on provider availability
        assert result.outcome in ("completed", "failed", "blocked")

    @pytest.mark.integration
    async def test_smoke_live_emits_events(self) -> None:
        """Test that smoke_live properly emits events to storage."""
        result = await smoke_live.execute(
            self.orchestrator,
            prompt="Short test",
            provider=None,
            model=None,
        )

        # Retrieve events from storage
        events = self.container.storage.list_events(result.task_id)

        # Should have at least: routed, and either execution_recorded or failed
        assert len(events) > 0, "No events emitted for task"

        event_types = {e.type for e in events}

        # Should include routing decision
        assert "llm.routed" in event_types, f"Missing llm.routed event. Got: {event_types}"

        # Should include either success or failure
        if result.outcome == "completed":
            assert "llm.execution_recorded" in event_types, f"Missing llm.execution_recorded. Got: {event_types}"
        else:
            assert (
                "task_failed" in event_types or "llm.budget_exceeded" in event_types
            ), f"Missing failure event for outcome={result.outcome}. Got: {event_types}"

    @pytest.mark.integration
    async def test_smoke_live_result_serializeable(self) -> None:
        """Test that SmokeResult can be serialized to dict/JSON."""
        result = await smoke_live.execute(
            self.orchestrator,
            prompt="test",
            provider=None,
            model=None,
        )

        # Should serialize to dict
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["project_id"] == result.project_id
        assert result_dict["outcome"] == result.outcome

        # Should be JSON serializable
        json_str = json.dumps(result_dict)
        assert json_str is not None
        assert len(json_str) > 0

        # Should deserialize back
        deserialized = json.loads(json_str)
        assert deserialized["project_id"] == result.project_id

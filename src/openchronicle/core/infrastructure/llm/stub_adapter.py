"""Stub LLM adapter for testing and default behavior."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

from openchronicle.core.domain.ports.llm_port import (
    LLMPort,
    LLMProviderError,
    LLMResponse,
    StreamChunk,
    ToolCall,
    ToolDefinition,
)


class StubLLMAdapter(LLMPort):
    """Simple stub LLM that returns truncated input for testing."""

    def __init__(self) -> None:
        self.model = "stub"

    async def complete_async(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_choice: str | None = None,
    ) -> LLMResponse:
        """Return a stub response based on input messages."""
        forced_error = os.getenv("OC_STUB_ERROR_CODE")
        if forced_error:
            raise LLMProviderError(
                "Stub adapter error requested",
                error_code=forced_error,
                hint="Unset OC_STUB_ERROR_CODE to restore normal stub responses.",
            )
        # Only use user messages

        # Tool call simulation via env var
        stub_tool_calls_raw = os.getenv("OC_STUB_TOOL_CALLS")
        if stub_tool_calls_raw and tools:
            import uuid

            parsed = json.loads(stub_tool_calls_raw)
            result_tool_calls = [
                ToolCall(
                    id=tc.get("id", f"stub_{uuid.uuid4().hex[:12]}"),
                    name=tc["name"],
                    arguments=tc.get("arguments", "{}"),
                )
                for tc in parsed
            ]
            return LLMResponse(
                content="",
                provider="stub",
                model=model or self.model,
                request_id=None,
                finish_reason="tool_calls",
                usage=None,
                latency_ms=0,
                tool_calls=result_tool_calls,
            )

        # Only use user messages for stub summary (ignore system prompts)
        user_messages = [msg.get("content", "") for msg in messages if msg.get("role") == "user"]
        text = " ".join(str(content) for content in user_messages if isinstance(content, str))

        meta_echo = os.getenv("OC_STUB_META_ECHO", "0") == "1"
        if meta_echo:
            ids_raw = os.getenv("OC_STUB_META_IDS", "")
            used_ids = [item.strip() for item in ids_raw.split(",") if item.strip()]
            meta = json.dumps({"used_memory_ids": used_ids}, sort_keys=True)
            summary = f"stub response\n<OC_META>{meta}</OC_META>"
        else:
            # Simple stub summarization: truncate to max length
            cleaned = " ".join(text.split())
            summary = cleaned if len(cleaned) <= 160 else cleaned[:150].rsplit(" ", 1)[0] + "..."

        return LLMResponse(
            content=summary,
            provider="stub",
            model=model or self.model,
            request_id=None,
            finish_reason="stop",
            usage=None,
            latency_ms=0,
        )

    async def stream_async(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_choice: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream stub response word by word for testing."""
        response = await self.complete_async(
            messages,
            model=model,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            provider=provider,
            tools=tools,
            tool_choice=tool_choice,
        )
        # If tool calls, yield single chunk (no word-by-word streaming)
        if response.tool_calls:
            yield StreamChunk(
                text="",
                finished=True,
                provider=response.provider,
                model=response.model,
                finish_reason=response.finish_reason,
                usage=response.usage,
                latency_ms=response.latency_ms,
                tool_calls=response.tool_calls,
            )
            return

        words = response.content.split()
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            text = word if i == 0 else " " + word
            yield StreamChunk(
                text=text,
                finished=is_last,
                provider=response.provider,
                model=response.model,
                finish_reason=response.finish_reason if is_last else None,
                usage=response.usage if is_last else None,
                latency_ms=response.latency_ms if is_last else None,
            )

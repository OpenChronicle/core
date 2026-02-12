from __future__ import annotations

import os
import time
from typing import Any

try:
    import groq
except ImportError:  # pragma: no cover - optional dependency
    groq = None  # type: ignore[assignment,unused-ignore]

from collections.abc import AsyncIterator

from openchronicle.core.domain.errors import CLIENT_MISSING, MISSING_API_KEY
from openchronicle.core.domain.ports.llm_port import LLMPort, LLMProviderError, LLMResponse, LLMUsage, StreamChunk


class GroqAdapter(LLMPort):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"
        self._client = self._build_client()

    def _build_client(self) -> Any:
        if not self.api_key:
            return None
        if groq is None:
            return None
        return groq.AsyncGroq(api_key=self.api_key)

    def _ensure_ready(self) -> None:
        if not self.api_key:
            raise LLMProviderError("GROQ_API_KEY not set", status_code=401, error_code=MISSING_API_KEY)
        if groq is None or self._client is None:
            raise LLMProviderError("groq package not installed", status_code=None, error_code=CLIENT_MISSING)

    async def complete_async(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
    ) -> LLMResponse:
        self._ensure_ready()

        start = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                max_tokens=max_output_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            code = getattr(exc, "code", None)
            raise LLMProviderError(str(exc), status_code=status, error_code=code) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        choice = response.choices[0]
        content = getattr(choice.message, "content", None) or ""
        finish_reason = getattr(choice, "finish_reason", None)
        usage = getattr(response, "usage", None)

        usage_obj = None
        if usage is not None:
            usage_obj = LLMUsage(
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            )

        return LLMResponse(
            content=content,
            provider="groq",
            model=model or self.model,
            request_id=getattr(response, "id", None),
            finish_reason=finish_reason,
            usage=usage_obj,
            latency_ms=latency_ms,
        )

    async def stream_async(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        provider: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        self._ensure_ready()

        start = time.perf_counter()
        try:
            stream = await self._client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                max_tokens=max_output_tokens,
                temperature=temperature,
                stream=True,
            )
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            code = getattr(exc, "code", None)
            raise LLMProviderError(str(exc), status_code=status, error_code=code) from exc

        finish_reason: str | None = None
        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None) or ""
            chunk_finish = getattr(chunk.choices[0], "finish_reason", None)
            if chunk_finish:
                finish_reason = chunk_finish

            # Groq includes usage on the final chunk
            usage_obj: LLMUsage | None = None
            chunk_usage = getattr(chunk, "x_groq", None)
            if chunk_usage is not None:
                usage_data = getattr(chunk_usage, "usage", None)
                if usage_data is not None:
                    usage_obj = LLMUsage(
                        input_tokens=getattr(usage_data, "prompt_tokens", None),
                        output_tokens=getattr(usage_data, "completion_tokens", None),
                        total_tokens=getattr(usage_data, "total_tokens", None),
                    )

            if text or chunk_finish:
                latency_ms = int((time.perf_counter() - start) * 1000) if chunk_finish else None
                yield StreamChunk(
                    text=text,
                    finished=bool(chunk_finish),
                    provider="groq",
                    model=model or self.model,
                    finish_reason=finish_reason if chunk_finish else None,
                    usage=usage_obj if chunk_finish else None,
                    latency_ms=latency_ms,
                )

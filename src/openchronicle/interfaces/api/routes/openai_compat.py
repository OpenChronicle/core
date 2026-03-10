"""OpenAI-compatible API — /v1/models and /v1/chat/completions.

Translation layer that lets OpenAI-compatible clients (Open WebUI,
etc.) talk to OC's LLM infrastructure.  Routes through OC's provider
routing and model config; does NOT create OC conversations or use memory.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from openchronicle.core.application.routing.router_policy import RouteDecision
from openchronicle.core.application.services.llm_execution import (
    execute_with_route,
    stream_with_route,
)
from openchronicle.core.domain.ports.llm_port import LLMProviderError
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.api.deps import get_container

logger = logging.getLogger(__name__)

router = APIRouter()

ContainerDep = Annotated[CoreContainer, Depends(get_container)]

# Fixed epoch for model "created" timestamps (models don't have creation dates).
_MODEL_EPOCH = 1_700_000_000


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str = Field(min_length=1, max_length=50)
    content: str = Field(max_length=200_000)


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="auto", max_length=200)
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=100_000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_route(container: CoreContainer, model_id: str) -> RouteDecision:
    """Turn an OpenAI-style model string into an OC RouteDecision.

    ``"auto"`` delegates to the default pool router.
    ``"provider/model"`` targets a specific provider and model.
    """
    if model_id == "auto":
        return container.router_policy.route(
            task_type="openai_compat",
            agent_role="worker",
        )

    if "/" not in model_id:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown model '{model_id}'. Use 'auto' for default routing "
                "or 'provider/model' format (e.g. 'openai/gpt-4o')."
            ),
        )

    provider, model = model_id.split("/", 1)

    # Validate the model exists in config
    entries = container.model_config_loader.list_enabled()
    match = any(e.provider == provider and e.model == model for e in entries)
    if not match:
        available = [f"{e.provider}/{e.model}" for e in entries]
        raise HTTPException(
            status_code=404,
            detail=(f"Model '{model_id}' not found. Available models: {available}"),
        )

    return RouteDecision(
        provider=provider,
        model=model,
        mode="explicit",
        reasons=[f"openai_compat:explicit:{model_id}"],
    )


def _messages_to_dicts(messages: list[ChatMessage]) -> list[dict[str, str]]:
    """Convert Pydantic ChatMessage list to plain dicts for the LLM port."""
    return [{"role": m.role, "content": m.content} for m in messages]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/models")
def list_models(container: ContainerDep) -> dict[str, Any]:
    """List available models in OpenAI format."""
    entries = container.model_config_loader.list_enabled()
    data = [
        {
            "id": f"{entry.provider}/{entry.model}",
            "object": "model",
            "created": _MODEL_EPOCH,
            "owned_by": entry.provider,
        }
        for entry in entries
    ]
    return {"object": "list", "data": data}


@router.post("/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    container: ContainerDep,
) -> Any:
    """Create a chat completion (streaming or non-streaming)."""
    route = _resolve_route(container, body.model)
    messages = _messages_to_dicts(body.messages)
    model_label = f"{route.provider}/{route.model}"

    if body.stream:
        return _streaming_response(container, route, messages, model_label, body)

    return await _non_streaming_response(container, route, messages, model_label, body)


async def _non_streaming_response(
    container: CoreContainer,
    route: RouteDecision,
    messages: list[dict[str, str]],
    model_label: str,
    body: ChatCompletionRequest,
) -> dict[str, Any]:
    """Execute a non-streaming chat completion and return OpenAI format."""
    try:
        response = await execute_with_route(
            llm=container.llm,
            route_decision=route,
            messages=messages,
            max_output_tokens=body.max_tokens,
            temperature=body.temperature,
        )
    except LLMProviderError as exc:
        logger.warning("OpenAI compat LLM error: %s", exc)
        raise HTTPException(
            status_code=exc.status_code or 502,
            detail=str(exc),
        ) from exc

    usage = response.usage
    return {
        "id": f"chatcmpl-{uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_label,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response.content},
                "finish_reason": response.finish_reason or "stop",
            }
        ],
        "usage": {
            "prompt_tokens": usage.input_tokens or 0 if usage else 0,
            "completion_tokens": usage.output_tokens or 0 if usage else 0,
            "total_tokens": usage.total_tokens or 0 if usage else 0,
        },
    }


def _streaming_response(
    container: CoreContainer,
    route: RouteDecision,
    messages: list[dict[str, str]],
    model_label: str,
    body: ChatCompletionRequest,
) -> StreamingResponse:
    """Return a StreamingResponse wrapping the SSE async generator."""
    completion_id = f"chatcmpl-{uuid4().hex[:12]}"

    async def event_generator() -> Any:
        created = int(time.time())
        first = True

        try:
            async for chunk in stream_with_route(
                llm=container.llm,
                route_decision=route,
                messages=messages,
                max_output_tokens=body.max_tokens,
                temperature=body.temperature,
            ):
                if first:
                    # First chunk includes role
                    delta: dict[str, str] = {"role": "assistant"}
                    if chunk.text:
                        delta["content"] = chunk.text
                    first = False
                elif chunk.finished:
                    delta = {}
                else:
                    delta = {"content": chunk.text} if chunk.text else {}

                finish_reason = chunk.finish_reason if chunk.finished else None
                if chunk.finished and not finish_reason:
                    finish_reason = "stop"

                sse_data = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model_label,
                    "choices": [
                        {
                            "index": 0,
                            "delta": delta,
                            "finish_reason": finish_reason,
                        }
                    ],
                }
                yield f"data: {json.dumps(sse_data)}\n\n"

            yield "data: [DONE]\n\n"
        except LLMProviderError as exc:
            logger.warning("OpenAI compat streaming error: %s", exc)
            error_data = {
                "error": {
                    "message": str(exc),
                    "type": "server_error",
                    "code": exc.error_code or "PROVIDER_ERROR",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

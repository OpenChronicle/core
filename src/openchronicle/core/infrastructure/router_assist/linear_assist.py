from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

from openchronicle.core.domain.errors.error_codes import CONFIG_ERROR, TIMEOUT
from openchronicle.core.domain.models.assist_result import RouterAssistResult
from openchronicle.core.domain.ports.llm_port import LLMProviderError
from openchronicle.core.domain.ports.router_assist_port import RouterAssistPort

_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9]+")


class LinearRouterAssist(RouterAssistPort):
    def __init__(self, *, model_path: str, timeout_ms: int = 50) -> None:
        self._timeout_ms = timeout_ms
        payload = _load_model_payload(model_path)

        version = str(payload.get("version", ""))
        if version != "1":
            raise LLMProviderError(
                f"Unsupported router assist model version: {version}",
                error_code=CONFIG_ERROR,
                hint="Use a router assist model with version '1'.",
            )

        bias_value = payload.get("bias")
        if not isinstance(bias_value, int | float):
            raise LLMProviderError(
                "Router assist model missing numeric bias",
                error_code=CONFIG_ERROR,
                hint="Ensure the model JSON includes a numeric 'bias' field.",
            )

        weights_value = payload.get("weights")
        if not isinstance(weights_value, dict):
            raise LLMProviderError(
                "Router assist model missing weights",
                error_code=CONFIG_ERROR,
                hint="Ensure the model JSON includes a 'weights' mapping.",
            )

        weights: dict[str, float] = {}
        for key, value in weights_value.items():
            if not isinstance(key, str):
                continue
            if not isinstance(value, int | float):
                continue
            weights[key.lower()] = float(value)

        token_limit = payload.get("token_limit")
        if token_limit is not None and (not isinstance(token_limit, int) or token_limit <= 0):
            token_limit = None

        self._bias = float(bias_value)
        self._weights = weights
        self._token_limit = token_limit

    def analyze(self, text: str, mode_hint: str | None = None) -> RouterAssistResult:
        _ = mode_hint
        started_at = time.perf_counter()
        tokens = _tokenize(text)
        if self._token_limit is not None:
            tokens = tokens[: self._token_limit]

        score = self._bias + sum(self._weights.get(token, 0.0) for token in tokens)
        probability = 1.0 / (1.0 + math.exp(-score))
        confidence = abs(probability - 0.5) * 2.0

        if self._timeout_ms > 0:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            if elapsed_ms > self._timeout_ms:
                raise LLMProviderError(
                    "Router assist exceeded time budget",
                    error_code=TIMEOUT,
                    hint="Increase OC_ROUTER_ASSIST_TIMEOUT_MS or disable router assist.",
                )

        reason_codes = ["assist.enabled", "assist.model_loaded"]
        if confidence >= 0.75:
            reason_codes.append("assist.high_confidence")

        return RouterAssistResult(
            nsfw_probability=probability,
            confidence=confidence,
            reason_codes=reason_codes,
            backend="linear",
        )


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    return [token for token in _TOKEN_SPLIT_RE.split(lowered) if token]


def _load_model_payload(model_path: str) -> dict[str, object]:
    path = Path(model_path)
    if not path.exists():
        raise LLMProviderError(
            f"Router assist model file not found: {model_path}",
            error_code=CONFIG_ERROR,
            hint="Set OC_ROUTER_ASSIST_MODEL_PATH to a valid model JSON file.",
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LLMProviderError(
            f"Failed to load router assist model: {model_path}",
            error_code=CONFIG_ERROR,
            hint="Ensure the router assist model JSON is readable and valid.",
        ) from exc

    if not isinstance(data, dict):
        raise LLMProviderError(
            "Router assist model must be a JSON object",
            error_code=CONFIG_ERROR,
            hint="Ensure the model JSON is an object with 'version', 'bias', and 'weights'.",
        )

    return data

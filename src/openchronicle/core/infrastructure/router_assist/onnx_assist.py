from __future__ import annotations

from openchronicle.core.domain.errors.error_codes import CONFIG_ERROR
from openchronicle.core.domain.models.assist_result import RouterAssistResult
from openchronicle.core.domain.ports.llm_port import LLMProviderError
from openchronicle.core.domain.ports.router_assist_port import RouterAssistPort


class OnnxRouterAssist(RouterAssistPort):
    def __init__(self, *, model_path: str, timeout_ms: int = 50) -> None:
        _ = model_path
        _ = timeout_ms
        raise LLMProviderError(
            "ONNX router assist backend is not available.",
            error_code=CONFIG_ERROR,
            hint="Use OC_ROUTER_ASSIST_BACKEND=linear or install onnxruntime support.",
        )

    def analyze(self, text: str, mode_hint: str | None = None) -> RouterAssistResult:
        _ = text
        _ = mode_hint
        raise LLMProviderError(
            "ONNX router assist backend is not available.",
            error_code=CONFIG_ERROR,
            hint="Use OC_ROUTER_ASSIST_BACKEND=linear or install onnxruntime support.",
        )

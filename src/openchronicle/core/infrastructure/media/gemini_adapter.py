"""Google Gemini/Imagen media generation adapter.

Uses the Gemini REST API ``/v1beta/models/{model}:predict`` endpoint
for Imagen models.  Auth via ``key`` query parameter (standard Gemini
pattern).  The adapter receives endpoint and API key from the resolved
model config.
"""

from __future__ import annotations

import base64
import logging
import time

import httpx

from openchronicle.core.domain.errors.error_codes import PROVIDER_ERROR, TIMEOUT
from openchronicle.core.domain.models.media import MediaRequest, MediaResult
from openchronicle.core.domain.ports.llm_port import LLMProviderError
from openchronicle.core.domain.ports.media_generation_port import MediaGenerationPort

logger = logging.getLogger(__name__)

# Aspect ratio mapping: (width, height) → Imagen aspect ratio string.
_ASPECT_RATIOS: dict[tuple[int, int], str] = {
    (1024, 1024): "1:1",
    (1536, 1024): "3:2",
    (1024, 1536): "2:3",
    (1280, 720): "16:9",
    (720, 1280): "9:16",
    (1024, 768): "4:3",
    (768, 1024): "3:4",
}


def _resolve_aspect_ratio(width: int | None, height: int | None) -> str | None:
    """Map width/height to the closest supported Imagen aspect ratio."""
    if width is None and height is None:
        return None
    w = width or 1024
    h = height or 1024
    key = (w, h)
    if key in _ASPECT_RATIOS:
        return _ASPECT_RATIOS[key]
    # Approximate: compute ratio and find closest match
    ratio = w / h
    best = min(_ASPECT_RATIOS.items(), key=lambda kv: abs(kv[0][0] / kv[0][1] - ratio))
    return best[1]


class GeminiMediaAdapter(MediaGenerationPort):
    """Media generation via Google Imagen models through the Gemini API."""

    def __init__(
        self,
        *,
        model: str = "imagen-3.0-generate-002",
        api_key: str,
        endpoint: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._base_endpoint = (endpoint or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self._timeout = timeout_seconds

    def generate(self, request: MediaRequest) -> MediaResult:
        model = request.model or self._model
        url = f"{self._base_endpoint}/models/{model}:predict"

        # Build Imagen predict payload
        parameters: dict = {"sampleCount": 1}
        aspect_ratio = _resolve_aspect_ratio(request.width, request.height)
        if aspect_ratio:
            parameters["aspectRatio"] = aspect_ratio

        payload: dict = {
            "instances": [{"prompt": request.prompt}],
            "parameters": parameters,
        }

        logger.info(
            "Gemini media generation: model=%s, prompt=%.60s...",
            model,
            request.prompt,
        )
        t0 = time.monotonic()

        try:
            response = httpx.post(
                url,
                json=payload,
                params={"key": self._api_key},
                headers={"Content-Type": "application/json"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(
                f"Gemini media generation failed: HTTP {exc.response.status_code}",
                error_code=PROVIDER_ERROR,
                details={"provider": "gemini", "model": model},
            ) from exc
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise LLMProviderError(
                f"Gemini connection failed: {type(exc).__name__}: {exc}",
                error_code=TIMEOUT,
                details={"provider": "gemini", "endpoint": url},
            ) from exc
        except Exception as exc:
            raise LLMProviderError(
                f"Gemini media generation failed: {type(exc).__name__}: {exc}",
                error_code=PROVIDER_ERROR,
                details={"provider": "gemini", "model": model},
            ) from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        image_data, mime_type = self._extract_image_data(data, model)

        return MediaResult(
            data=image_data,
            media_type=request.media_type,
            mime_type=mime_type,
            width=request.width,
            height=request.height,
            model=model,
            provider="gemini",
            seed=request.seed,
            latency_ms=elapsed_ms,
            metadata={"aspect_ratio": aspect_ratio} if aspect_ratio else {},
        )

    def supported_media_types(self) -> list[str]:
        return ["image"]

    def model_name(self) -> str:
        return self._model

    @staticmethod
    def _extract_image_data(data: dict, model: str) -> tuple[bytes, str]:
        """Extract base64-decoded image bytes from Imagen predict response.

        Response format::

            {"predictions": [{"bytesBase64Encoded": "...", "mimeType": "image/png"}]}

        Returns (image_bytes, mime_type).
        """
        predictions = data.get("predictions")
        if predictions and isinstance(predictions, list) and len(predictions) > 0:
            pred = predictions[0]
            b64 = pred.get("bytesBase64Encoded")
            if b64 and isinstance(b64, str):
                mime = pred.get("mimeType", "image/png")
                return base64.b64decode(b64), str(mime)

        raise LLMProviderError(
            f"Gemini response for model '{model}' contained no image data. Response keys: {list(data.keys())}",
            error_code=PROVIDER_ERROR,
            details={"provider": "gemini", "model": model, "keys": list(data.keys())},
        )

"""Tests for media generation: port, adapters, use case, settings, container wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openchronicle.core.application.config.settings import (
    MediaSettings,
    load_media_settings,
)
from openchronicle.core.domain.exceptions import ValidationError
from openchronicle.core.domain.models.media import MediaRequest, MediaResult
from openchronicle.core.domain.ports.media_generation_port import MediaGenerationPort
from openchronicle.core.infrastructure.media.stub_adapter import StubMediaAdapter

# ── Domain models ──────────────────────────────────────────────────


class TestMediaRequest:
    def test_defaults(self) -> None:
        r = MediaRequest(prompt="a cat")
        assert r.prompt == "a cat"
        assert r.media_type == "image"
        assert r.model is None
        assert r.width is None
        assert r.seed is None
        assert r.steps is None
        assert r.duration_seconds is None
        assert r.fps is None

    def test_video_fields(self) -> None:
        r = MediaRequest(
            prompt="a sunset",
            media_type="video",
            duration_seconds=5.0,
            fps=24,
        )
        assert r.media_type == "video"
        assert r.duration_seconds == 5.0
        assert r.fps == 24


class TestMediaResult:
    def test_defaults(self) -> None:
        r = MediaResult(data=b"\x00", media_type="image", mime_type="image/png")
        assert r.model == ""
        assert r.provider == ""
        assert r.latency_ms == 0.0
        assert r.metadata == {}
        assert r.seed is None


# ── Port ABC ───────────────────────────────────────────────────────


class TestMediaGenerationPort:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            MediaGenerationPort()  # type: ignore[abstract]

    def test_stub_implements_port(self) -> None:
        adapter = StubMediaAdapter()
        assert isinstance(adapter, MediaGenerationPort)


# ── Stub adapter ───────────────────────────────────────────────────


class TestStubMediaAdapter:
    def test_generate_returns_valid_png(self) -> None:
        adapter = StubMediaAdapter()
        request = MediaRequest(prompt="a cat sitting on a mat")
        result = adapter.generate(request)

        assert result.media_type == "image"
        assert result.mime_type == "image/png"
        assert result.provider == "stub"
        assert result.model == "stub-media"
        assert result.width == 1
        assert result.height == 1
        assert result.latency_ms >= 0
        assert result.seed is not None
        # PNG signature check
        assert result.data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_deterministic_output(self) -> None:
        adapter = StubMediaAdapter()
        r1 = adapter.generate(MediaRequest(prompt="same prompt"))
        r2 = adapter.generate(MediaRequest(prompt="same prompt"))
        assert r1.data == r2.data
        assert r1.seed == r2.seed

    def test_different_prompts_different_output(self) -> None:
        adapter = StubMediaAdapter()
        r1 = adapter.generate(MediaRequest(prompt="cat"))
        r2 = adapter.generate(MediaRequest(prompt="dog"))
        assert r1.data != r2.data

    def test_explicit_seed_preserved(self) -> None:
        adapter = StubMediaAdapter()
        result = adapter.generate(MediaRequest(prompt="test", seed=42))
        assert result.seed == 42

    def test_supported_media_types(self) -> None:
        adapter = StubMediaAdapter()
        assert adapter.supported_media_types() == ["image"]

    def test_model_name(self) -> None:
        adapter = StubMediaAdapter(model="custom-stub")
        assert adapter.model_name() == "custom-stub"

    def test_custom_model_in_result(self) -> None:
        adapter = StubMediaAdapter(model="my-model")
        result = adapter.generate(MediaRequest(prompt="test"))
        assert result.model == "my-model"


# ── Ollama adapter (unit tests — no network) ──────────────────────


class TestOllamaMediaAdapter:
    def test_init_defaults(self) -> None:
        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        adapter = OllamaMediaAdapter()
        assert adapter.model_name() == "flux"
        assert adapter.supported_media_types() == ["image"]
        assert adapter._host == "http://localhost:11434"
        assert adapter._timeout == 120.0

    def test_init_custom(self) -> None:
        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        adapter = OllamaMediaAdapter(
            model="sdxl",
            host="http://myhost:8080",
            timeout_seconds=60.0,
            supported_types=["image", "video"],
        )
        assert adapter.model_name() == "sdxl"
        assert adapter._host == "http://myhost:8080"
        assert adapter._timeout == 60.0
        assert adapter.supported_media_types() == ["image", "video"]

    def test_init_from_env(self) -> None:
        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        with patch.dict("os.environ", {"OLLAMA_HOST": "http://envhost:1234"}):
            adapter = OllamaMediaAdapter()
            assert adapter._host == "http://envhost:1234"

    def test_generate_success(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        fake_image = b"\x89PNG\r\n\x1a\nfakedata"
        response_json = {"images": [base64.b64encode(fake_image).decode()]}

        mock_response = MagicMock()
        mock_response.json.return_value = response_json
        mock_response.raise_for_status = MagicMock()

        adapter = OllamaMediaAdapter(model="flux")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = adapter.generate(MediaRequest(prompt="a landscape"))

        assert result.data == fake_image
        assert result.provider == "ollama"
        assert result.model == "flux"
        assert result.latency_ms > 0

        # Verify request payload
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"] if "json" in call_kwargs.kwargs else call_kwargs[1]["json"]
        assert payload["model"] == "flux"
        assert payload["prompt"] == "a landscape"
        assert payload["stream"] is False

    def test_generate_with_options(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"images": [base64.b64encode(b"img").decode()]}
        mock_response.raise_for_status = MagicMock()

        adapter = OllamaMediaAdapter()
        with patch("httpx.post", return_value=mock_response) as mock_post:
            adapter.generate(
                MediaRequest(
                    prompt="test",
                    width=512,
                    height=768,
                    seed=42,
                    steps=20,
                    negative_prompt="blurry",
                )
            )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["width"] == 512
        assert payload["height"] == 768
        assert payload["negative_prompt"] == "blurry"
        assert payload["options"]["seed"] == 42
        assert payload["options"]["num_predict"] == 20

    def test_generate_model_override(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"images": [base64.b64encode(b"x").decode()]}
        mock_response.raise_for_status = MagicMock()

        adapter = OllamaMediaAdapter(model="flux")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = adapter.generate(MediaRequest(prompt="test", model="sdxl"))

        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "sdxl"
        assert result.model == "sdxl"

    def test_generate_http_error(self) -> None:
        import httpx

        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        adapter = OllamaMediaAdapter()
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(LLMProviderError, match="HTTP 404"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_generate_timeout(self) -> None:
        import httpx

        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        adapter = OllamaMediaAdapter()
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(LLMProviderError, match="TimeoutException"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_generate_no_image_in_response(self) -> None:
        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "some text, not base64"}
        mock_response.raise_for_status = MagicMock()

        adapter = OllamaMediaAdapter()
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(LLMProviderError, match="no image data"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_extract_image_fallback_image_field(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter

        img = b"rawbytes"
        data = {"image": base64.b64encode(img).decode()}
        assert OllamaMediaAdapter._extract_image_data(data, "test") == img


# ── Use case ───────────────────────────────────────────────────────


class TestGenerateMediaUseCase:
    def _make_deps(self) -> tuple:
        from openchronicle.core.application.services.asset_storage import AssetFileStorage

        port = StubMediaAdapter()
        store = MagicMock()
        store.get_asset_by_hash.return_value = None
        file_storage = MagicMock(spec=AssetFileStorage)
        file_storage.compute_hash.return_value = "abc123"
        file_storage.store_bytes.return_value = "proj/asset.png"
        events: list = []
        return port, store, file_storage, events.append, events

    def test_generate_creates_asset(self) -> None:
        from openchronicle.core.application.use_cases import generate_media

        port, store, file_storage, emit, events = self._make_deps()
        request = MediaRequest(prompt="a cat")

        result, asset, is_new = generate_media.execute(
            media_port=port,
            asset_store=store,
            file_storage=file_storage,
            emit_event=emit,
            project_id="proj-1",
            request=request,
        )

        assert is_new is True
        assert asset.project_id == "proj-1"
        assert asset.mime_type == "image/png"
        assert asset.content_hash == "abc123"
        assert result.provider == "stub"
        store.add_asset.assert_called_once()
        assert any(e.type == "media.generated" for e in events)

    def test_generate_dedup(self) -> None:
        from openchronicle.core.application.use_cases import generate_media

        port, store, file_storage, emit, events = self._make_deps()
        existing_asset = MagicMock()
        existing_asset.id = "existing-id"
        store.get_asset_by_hash.return_value = existing_asset

        result, asset, is_new = generate_media.execute(
            media_port=port,
            asset_store=store,
            file_storage=file_storage,
            emit_event=emit,
            project_id="proj-1",
            request=MediaRequest(prompt="a cat"),
        )

        assert is_new is False
        assert asset.id == "existing-id"
        store.add_asset.assert_not_called()

    def test_empty_prompt_raises(self) -> None:
        from openchronicle.core.application.use_cases import generate_media

        port, store, file_storage, emit, events = self._make_deps()

        with pytest.raises(ValidationError, match="prompt must not be empty"):
            generate_media.execute(
                media_port=port,
                asset_store=store,
                file_storage=file_storage,
                emit_event=emit,
                project_id="proj-1",
                request=MediaRequest(prompt="   "),
            )

    def test_unsupported_media_type_raises(self) -> None:
        from openchronicle.core.application.use_cases import generate_media

        port, store, file_storage, emit, events = self._make_deps()

        with pytest.raises(ValidationError, match="not supported"):
            generate_media.execute(
                media_port=port,
                asset_store=store,
                file_storage=file_storage,
                emit_event=emit,
                project_id="proj-1",
                request=MediaRequest(prompt="a video", media_type="video"),
            )

    def test_event_payload_includes_details(self) -> None:
        from openchronicle.core.application.use_cases import generate_media

        port, store, file_storage, emit, events = self._make_deps()

        generate_media.execute(
            media_port=port,
            asset_store=store,
            file_storage=file_storage,
            emit_event=emit,
            project_id="proj-1",
            request=MediaRequest(prompt="a landscape at sunset"),
        )

        media_event = next(e for e in events if e.type == "media.generated")
        assert media_event.payload["model"] == "stub-media"
        assert media_event.payload["provider"] == "stub"
        assert media_event.payload["media_type"] == "image"
        assert media_event.payload["prompt_preview"] == "a landscape at sunset"

    def test_linking(self) -> None:
        from openchronicle.core.application.use_cases import generate_media

        port, store, file_storage, emit, events = self._make_deps()

        generate_media.execute(
            media_port=port,
            asset_store=store,
            file_storage=file_storage,
            emit_event=emit,
            project_id="proj-1",
            request=MediaRequest(prompt="a cat"),
            link_target_type="conversation",
            link_target_id="conv-1",
            link_role="output",
        )

        store.add_asset_link.assert_called_once()
        link = store.add_asset_link.call_args[0][0]
        assert link.target_type == "conversation"
        assert link.target_id == "conv-1"
        assert link.role == "output"
        assert any(e.type == "asset.linked" for e in events)


# ── Settings ───────────────────────────────────────────────────────


class TestMediaSettings:
    def test_defaults(self) -> None:
        s = MediaSettings()
        assert s.model == ""
        assert s.timeout == 120.0
        assert s.enabled is False

    def test_enabled_when_model_set(self) -> None:
        s = MediaSettings(model="flux")
        assert s.enabled is True

    def test_stub_model(self) -> None:
        s = MediaSettings(model="stub")
        assert s.enabled is True

    def test_invalid_timeout(self) -> None:
        with pytest.raises(ValueError, match="media timeout"):
            MediaSettings(timeout=0)

    def test_frozen(self) -> None:
        s = MediaSettings()
        with pytest.raises(AttributeError):
            s.model = "stub"  # type: ignore[misc]

    def test_load_defaults(self) -> None:
        s = load_media_settings()
        assert s.model == ""
        assert s.enabled is False
        assert s.timeout == 120.0

    def test_load_from_file_config(self) -> None:
        s = load_media_settings({"model": "flux", "timeout": 60})
        assert s.model == "flux"
        assert s.timeout == 60.0

    def test_load_env_overrides(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "OC_MEDIA_MODEL": "gpt-image-1",
                "OC_MEDIA_TIMEOUT": "90",
            },
        ):
            s = load_media_settings({"model": "flux"})
            assert s.model == "gpt-image-1"
            assert s.timeout == 90.0


# ── OpenAI adapter (unit tests — no network) ─────────────────────


class TestOpenAIMediaAdapter:
    def test_init_defaults(self) -> None:
        from openchronicle.core.infrastructure.media.openai_adapter import OpenAIMediaAdapter

        adapter = OpenAIMediaAdapter(api_key="test-key")
        assert adapter.model_name() == "gpt-image-1"
        assert adapter.supported_media_types() == ["image"]

    def test_generate_success(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.openai_adapter import OpenAIMediaAdapter

        fake_image = b"\x89PNG\r\n\x1a\nfakedata"
        response_json = {"data": [{"b64_json": base64.b64encode(fake_image).decode()}]}

        mock_response = MagicMock()
        mock_response.json.return_value = response_json
        mock_response.raise_for_status = MagicMock()

        adapter = OpenAIMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = adapter.generate(MediaRequest(prompt="a landscape"))

        assert result.data == fake_image
        assert result.provider == "openai"
        assert result.model == "gpt-image-1"
        assert result.latency_ms > 0

        # Verify auth header
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
        assert headers["Authorization"] == "Bearer test-key"

    def test_generate_with_size(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.openai_adapter import OpenAIMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"b64_json": base64.b64encode(b"img").decode()}]}
        mock_response.raise_for_status = MagicMock()

        adapter = OpenAIMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            adapter.generate(MediaRequest(prompt="test", width=1536, height=1024))

        payload = mock_post.call_args.kwargs["json"]
        assert payload["size"] == "1536x1024"

    def test_generate_http_error(self) -> None:
        import httpx

        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.openai_adapter import OpenAIMediaAdapter

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )

        adapter = OpenAIMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(LLMProviderError, match="HTTP 400"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_generate_timeout(self) -> None:
        import httpx

        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.openai_adapter import OpenAIMediaAdapter

        adapter = OpenAIMediaAdapter(api_key="test-key")
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(LLMProviderError, match="TimeoutException"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_no_image_in_response(self) -> None:
        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.openai_adapter import OpenAIMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        adapter = OpenAIMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(LLMProviderError, match="no image data"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_custom_endpoint(self) -> None:
        from openchronicle.core.infrastructure.media.openai_adapter import OpenAIMediaAdapter

        adapter = OpenAIMediaAdapter(api_key="test-key", endpoint="http://custom:8080/v1/images/generations")
        assert adapter._endpoint == "http://custom:8080/v1/images/generations"


# ── Gemini adapter (unit tests — no network) ─────────────────────


class TestGeminiMediaAdapter:
    def test_init_defaults(self) -> None:
        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter

        adapter = GeminiMediaAdapter(api_key="test-key")
        assert adapter.model_name() == "gemini-2.0-flash-exp-image-generation"
        assert adapter.supported_media_types() == ["image"]

    def test_native_generate_success(self) -> None:
        """Gemini native model uses :generateContent with inlineData response."""
        import base64

        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter

        fake_image = b"\x89PNG\r\n\x1a\nfakedata"
        response_json = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(fake_image).decode()}}
                        ]
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = response_json
        mock_response.raise_for_status = MagicMock()

        adapter = GeminiMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = adapter.generate(MediaRequest(prompt="a sunset"))

        assert result.data == fake_image
        assert result.provider == "gemini"
        assert result.mime_type == "image/png"
        assert result.metadata["surface"] == "generateContent"

        # Verify x-goog-api-key header
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers", {})
        assert headers["x-goog-api-key"] == "test-key"

        # Verify generateContent payload
        payload = call_kwargs.kwargs["json"]
        assert "contents" in payload
        assert payload["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]

    def test_imagen_predict_success(self) -> None:
        """Imagen model uses :predict with predictions response."""
        import base64

        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter

        fake_image = b"\x89PNG\r\n\x1a\nfakedata"
        response_json = {
            "predictions": [{"bytesBase64Encoded": base64.b64encode(fake_image).decode(), "mimeType": "image/png"}]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = response_json
        mock_response.raise_for_status = MagicMock()

        adapter = GeminiMediaAdapter(api_key="test-key", model="imagen-4.0-generate-001")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = adapter.generate(MediaRequest(prompt="a sunset"))

        assert result.data == fake_image
        assert result.metadata["surface"] == "predict"

        # Verify :predict URL
        url = mock_post.call_args.args[0] if mock_post.call_args.args else mock_post.call_args.kwargs.get("url", "")
        assert ":predict" in str(url)

    def test_imagen_with_aspect_ratio(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "predictions": [{"bytesBase64Encoded": base64.b64encode(b"img").decode(), "mimeType": "image/png"}]
        }
        mock_response.raise_for_status = MagicMock()

        adapter = GeminiMediaAdapter(api_key="test-key", model="imagen-4.0-generate-001")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            adapter.generate(MediaRequest(prompt="test", width=1536, height=1024))

        payload = mock_post.call_args.kwargs["json"]
        assert payload["parameters"]["aspectRatio"] == "3:2"

    def test_generate_http_error(self) -> None:
        import httpx

        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_response
        )

        adapter = GeminiMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(LLMProviderError, match="HTTP 403"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_generate_timeout(self) -> None:
        import httpx

        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter

        adapter = GeminiMediaAdapter(api_key="test-key")
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(LLMProviderError, match="TimeoutException"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_no_image_in_native_response(self) -> None:
        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"candidates": [{"content": {"parts": [{"text": "no image"}]}}]}
        mock_response.raise_for_status = MagicMock()

        adapter = GeminiMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(LLMProviderError, match="no image data"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_no_predictions_in_imagen_response(self) -> None:
        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"predictions": []}
        mock_response.raise_for_status = MagicMock()

        adapter = GeminiMediaAdapter(api_key="test-key", model="imagen-4.0-generate-001")
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(LLMProviderError, match="no image data"):
                adapter.generate(MediaRequest(prompt="test"))


# ── xAI adapter (unit tests — no network) ─────────────────────────


class TestXAIMediaAdapter:
    def test_init_defaults(self) -> None:
        from openchronicle.core.infrastructure.media.xai_adapter import XAIMediaAdapter

        adapter = XAIMediaAdapter(api_key="test-key")
        assert adapter.model_name() == "grok-imagine-image"
        assert adapter.supported_media_types() == ["image"]

    def test_generate_success(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.xai_adapter import XAIMediaAdapter

        fake_image = b"\x89PNG\r\n\x1a\nfakedata"
        response_json = {"data": [{"b64_json": base64.b64encode(fake_image).decode()}]}

        mock_response = MagicMock()
        mock_response.json.return_value = response_json
        mock_response.raise_for_status = MagicMock()

        adapter = XAIMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = adapter.generate(MediaRequest(prompt="a landscape"))

        assert result.data == fake_image
        assert result.provider == "xai"
        assert result.model == "grok-imagine-image"

        # Verify auth header
        headers = mock_post.call_args.kwargs.get("headers", {})
        assert headers["Authorization"] == "Bearer test-key"

        # Verify aspect_ratio in payload
        payload = mock_post.call_args.kwargs["json"]
        assert payload["response_format"] == "b64_json"
        assert "aspect_ratio" in payload

    def test_generate_with_aspect_ratio(self) -> None:
        import base64

        from openchronicle.core.infrastructure.media.xai_adapter import XAIMediaAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"b64_json": base64.b64encode(b"img").decode()}]}
        mock_response.raise_for_status = MagicMock()

        adapter = XAIMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response) as mock_post:
            adapter.generate(MediaRequest(prompt="test", width=1280, height=720))

        payload = mock_post.call_args.kwargs["json"]
        assert payload["aspect_ratio"] == "16:9"

    def test_generate_http_error(self) -> None:
        import httpx

        from openchronicle.core.domain.ports.llm_port import LLMProviderError
        from openchronicle.core.infrastructure.media.xai_adapter import XAIMediaAdapter

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        adapter = XAIMediaAdapter(api_key="test-key")
        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(LLMProviderError, match="HTTP 401"):
                adapter.generate(MediaRequest(prompt="test"))

    def test_custom_endpoint(self) -> None:
        from openchronicle.core.infrastructure.media.xai_adapter import XAIMediaAdapter

        adapter = XAIMediaAdapter(api_key="test-key", endpoint="http://custom:8080/v1/images/generations")
        assert adapter._endpoint == "http://custom:8080/v1/images/generations"


# ── Model config: type field and media lookup ─────────────────────


class TestModelConfigMediaLookup:
    def _write_config(self, config_dir: Path, filename: str, data: dict) -> None:
        import json

        models_dir = config_dir / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        (models_dir / filename).write_text(json.dumps(data))

    def test_type_field_parsed(self, tmp_path: Path) -> None:
        from openchronicle.core.application.config.model_config import ModelConfigLoader

        self._write_config(
            tmp_path,
            "ollama_flux.json",
            {"provider": "ollama", "model": "flux", "type": "media", "capabilities": {"image_generation": True}},
        )
        loader = ModelConfigLoader(str(tmp_path))
        configs = loader.list_all()
        assert len(configs) == 1
        assert configs[0].type == "media"

    def test_type_field_defaults_to_llm(self, tmp_path: Path) -> None:
        from openchronicle.core.application.config.model_config import ModelConfigLoader

        self._write_config(
            tmp_path,
            "openai_gpt4o.json",
            {"provider": "openai", "model": "gpt-4o"},
        )
        loader = ModelConfigLoader(str(tmp_path))
        assert loader.list_all()[0].type == "llm"

    def test_description_field_parsed(self, tmp_path: Path) -> None:
        from openchronicle.core.application.config.model_config import ModelConfigLoader

        self._write_config(
            tmp_path,
            "test.json",
            {"provider": "openai", "model": "test", "description": "A test model"},
        )
        loader = ModelConfigLoader(str(tmp_path))
        assert loader.list_all()[0].description == "A test model"

    def test_find_media_model(self, tmp_path: Path) -> None:
        from openchronicle.core.application.config.model_config import ModelConfigLoader

        self._write_config(
            tmp_path,
            "llm.json",
            {"provider": "openai", "model": "gpt-4o", "capabilities": {"text_generation": True}},
        )
        self._write_config(
            tmp_path,
            "media.json",
            {"provider": "ollama", "model": "flux", "capabilities": {"image_generation": True}},
        )
        loader = ModelConfigLoader(str(tmp_path))

        # Find by name
        cfg = loader.find_media_model("flux")
        assert cfg is not None
        assert cfg.model == "flux"
        assert cfg.provider == "ollama"

        # Non-media model not found
        assert loader.find_media_model("gpt-4o") is None

    def test_find_media_model_empty_returns_first(self, tmp_path: Path) -> None:
        from openchronicle.core.application.config.model_config import ModelConfigLoader

        self._write_config(
            tmp_path,
            "flux.json",
            {"provider": "ollama", "model": "flux", "capabilities": {"image_generation": True}},
        )
        loader = ModelConfigLoader(str(tmp_path))
        cfg = loader.find_media_model("")
        assert cfg is not None
        assert cfg.model == "flux"

    def test_find_media_model_not_found(self, tmp_path: Path) -> None:
        from openchronicle.core.application.config.model_config import ModelConfigLoader

        self._write_config(
            tmp_path,
            "llm.json",
            {"provider": "openai", "model": "gpt-4o"},
        )
        loader = ModelConfigLoader(str(tmp_path))
        assert loader.find_media_model("flux") is None

    def test_list_by_capability(self, tmp_path: Path) -> None:
        from openchronicle.core.application.config.model_config import ModelConfigLoader

        self._write_config(
            tmp_path,
            "llm.json",
            {"provider": "openai", "model": "gpt-4o", "capabilities": {"text_generation": True}},
        )
        self._write_config(
            tmp_path,
            "flux.json",
            {"provider": "ollama", "model": "flux", "capabilities": {"image_generation": True}},
        )
        self._write_config(
            tmp_path,
            "imagen.json",
            {"provider": "gemini", "model": "imagen-3", "capabilities": {"image_generation": True}},
        )
        loader = ModelConfigLoader(str(tmp_path))
        media_models = loader.list_by_capability("image_generation")
        assert len(media_models) == 2
        assert {c.model for c in media_models} == {"flux", "imagen-3"}


# ── Container wiring ──────────────────────────────────────────────


def _setup_config_dir(tmp_path: Path, model_configs: list[tuple[str, dict]] | None = None) -> Path:
    """Create a config dir with optional model config files."""
    import json

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    if model_configs:
        models_dir = config_dir / "models"
        models_dir.mkdir()
        for filename, data in model_configs:
            (models_dir / filename).write_text(json.dumps(data))
    return config_dir


class TestMediaContainerWiring:
    def test_media_port_none_by_default(self, tmp_path: Path) -> None:
        """When OC_MEDIA_MODEL is empty, media_port is None."""
        from openchronicle.core.infrastructure.wiring.container import CoreContainer

        config_dir = _setup_config_dir(tmp_path)
        with CoreContainer(
            db_path=str(tmp_path / "test.db"),
            config_dir=str(config_dir),
        ) as c:
            assert c.media_port is None

    def test_media_port_stub(self, tmp_path: Path) -> None:
        """When OC_MEDIA_MODEL is 'stub', media_port is a StubMediaAdapter."""
        from openchronicle.core.infrastructure.wiring.container import CoreContainer

        config_dir = _setup_config_dir(tmp_path)
        with patch.dict("os.environ", {"OC_MEDIA_MODEL": "stub"}, clear=False):
            with CoreContainer(
                db_path=str(tmp_path / "test.db"),
                config_dir=str(config_dir),
            ) as c:
                assert c.media_port is not None
                assert isinstance(c.media_port, StubMediaAdapter)

    def test_media_port_ollama_from_config(self, tmp_path: Path) -> None:
        """When OC_MEDIA_MODEL matches an Ollama media config, OllamaMediaAdapter is created."""
        from openchronicle.core.infrastructure.media.ollama_adapter import OllamaMediaAdapter
        from openchronicle.core.infrastructure.wiring.container import CoreContainer

        config_dir = _setup_config_dir(
            tmp_path,
            [
                (
                    "ollama_flux.json",
                    {
                        "provider": "ollama",
                        "model": "flux",
                        "capabilities": {"image_generation": True},
                        "api_config": {"default_base_url": "http://localhost:11434", "timeout": 120},
                    },
                )
            ],
        )
        with patch.dict("os.environ", {"OC_MEDIA_MODEL": "flux"}, clear=False):
            with CoreContainer(
                db_path=str(tmp_path / "test.db"),
                config_dir=str(config_dir),
            ) as c:
                assert c.media_port is not None
                assert isinstance(c.media_port, OllamaMediaAdapter)
                assert c.media_port.model_name() == "flux"

    def test_media_port_openai_from_config(self, tmp_path: Path) -> None:
        """When OC_MEDIA_MODEL matches an OpenAI media config, OpenAIMediaAdapter is created."""
        from openchronicle.core.infrastructure.media.openai_adapter import OpenAIMediaAdapter
        from openchronicle.core.infrastructure.wiring.container import CoreContainer

        config_dir = _setup_config_dir(
            tmp_path,
            [
                (
                    "openai_gpt_image.json",
                    {
                        "provider": "openai",
                        "model": "gpt-image-1",
                        "capabilities": {"image_generation": True},
                        "api_config": {
                            "endpoint": "https://api.openai.com/v1/images/generations",
                            "auth_header": "Authorization",
                            "auth_format": "Bearer {api_key}",
                        },
                    },
                )
            ],
        )
        with patch.dict(
            "os.environ",
            {"OC_MEDIA_MODEL": "gpt-image-1", "OPENAI_API_KEY": "test-key"},
            clear=False,
        ):
            with CoreContainer(
                db_path=str(tmp_path / "test.db"),
                config_dir=str(config_dir),
            ) as c:
                assert c.media_port is not None
                assert isinstance(c.media_port, OpenAIMediaAdapter)
                assert c.media_port.model_name() == "gpt-image-1"

    def test_media_port_gemini_from_config(self, tmp_path: Path) -> None:
        """When OC_MEDIA_MODEL matches a Gemini media config, GeminiMediaAdapter is created."""
        from openchronicle.core.infrastructure.media.gemini_adapter import GeminiMediaAdapter
        from openchronicle.core.infrastructure.wiring.container import CoreContainer

        config_dir = _setup_config_dir(
            tmp_path,
            [
                (
                    "gemini_image.json",
                    {
                        "provider": "gemini",
                        "model": "gemini-2.0-flash-exp-image-generation",
                        "capabilities": {"image_generation": True},
                        "api_config": {
                            "endpoint": "https://generativelanguage.googleapis.com/v1beta",
                        },
                    },
                )
            ],
        )
        with patch.dict(
            "os.environ",
            {"OC_MEDIA_MODEL": "gemini-2.0-flash-exp-image-generation", "GEMINI_API_KEY": "test-key"},
            clear=False,
        ):
            with CoreContainer(
                db_path=str(tmp_path / "test.db"),
                config_dir=str(config_dir),
            ) as c:
                assert c.media_port is not None
                assert isinstance(c.media_port, GeminiMediaAdapter)
                assert c.media_port.model_name() == "gemini-2.0-flash-exp-image-generation"

    def test_media_port_unknown_model_graceful(self, tmp_path: Path) -> None:
        """Unknown model name results in media_port = None (graceful degradation)."""
        from openchronicle.core.infrastructure.wiring.container import CoreContainer

        config_dir = _setup_config_dir(tmp_path)
        with patch.dict("os.environ", {"OC_MEDIA_MODEL": "nonexistent-model"}, clear=False):
            with CoreContainer(
                db_path=str(tmp_path / "test.db"),
                config_dir=str(config_dir),
            ) as c:
                assert c.media_port is None

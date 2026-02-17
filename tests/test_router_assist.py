from __future__ import annotations

from pathlib import Path

import pytest

from openchronicle.core.domain.errors.error_codes import CONFIG_ERROR
from openchronicle.core.domain.ports.llm_port import LLMProviderError
from openchronicle.core.infrastructure.router_assist.linear_assist import LinearRouterAssist
from openchronicle.core.infrastructure.routing.hybrid_router import HybridInteractionRouter
from openchronicle.core.infrastructure.routing.rule_router import RuleInteractionRouter
from openchronicle.core.infrastructure.wiring.container import CoreContainer


def _fixture_model_path() -> str:
    return str(Path(__file__).resolve().parent / "fixtures" / "router_assist_linear_model.json")


def test_linear_router_assist_scores() -> None:
    assist = LinearRouterAssist(model_path=_fixture_model_path(), timeout_ms=50)

    high = assist.analyze("nsfw")
    low = assist.analyze("hello friend")

    assert high.nsfw_probability > 0.7
    assert low.nsfw_probability < 0.4


def test_hybrid_router_combines_scores() -> None:
    assist = LinearRouterAssist(model_path=_fixture_model_path(), timeout_ms=50)
    base_router = RuleInteractionRouter(router_log_reasons=True)
    hybrid = HybridInteractionRouter(base_router=base_router, assist=assist)

    base_hint = base_router.analyze(user_text="nsfw", recent_turns=[])
    assist_hint = assist.analyze("nsfw")
    hybrid_hint = hybrid.analyze(user_text="nsfw", recent_turns=[])

    assert base_hint.nsfw_score < assist_hint.nsfw_probability
    assert hybrid_hint.nsfw_score == pytest.approx(assist_hint.nsfw_probability)
    assert hybrid_hint.requires_nsfw_capable_model
    assert "nsfw" not in " ".join(hybrid_hint.reason_codes)

    low_hint = hybrid.analyze(user_text="roleplay a scene", recent_turns=[])
    assert low_hint.requires_nsfw_capable_model is False


def test_router_assist_missing_model_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OC_ROUTER_ASSIST_ENABLED", "1")
    monkeypatch.delenv("OC_ROUTER_ASSIST_MODEL_PATH", raising=False)

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "plugins").mkdir(parents=True, exist_ok=True)
    (tmp_path / "output").mkdir(parents=True, exist_ok=True)

    with pytest.raises(LLMProviderError) as exc:
        CoreContainer(
            db_path=str(tmp_path / "db.sqlite"),
            config_dir=str(tmp_path / "config"),
            plugin_dir=str(tmp_path / "plugins"),
            output_dir=str(tmp_path / "output"),
        )

    assert exc.value.error_code == CONFIG_ERROR


def test_router_assist_onnx_backend_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OC_ROUTER_ASSIST_ENABLED", "1")
    monkeypatch.setenv("OC_ROUTER_ASSIST_BACKEND", "onnx")
    monkeypatch.setenv("OC_ROUTER_ASSIST_MODEL_PATH", _fixture_model_path())

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "plugins").mkdir(parents=True, exist_ok=True)
    (tmp_path / "output").mkdir(parents=True, exist_ok=True)

    with pytest.raises(LLMProviderError) as exc:
        CoreContainer(
            db_path=str(tmp_path / "db.sqlite"),
            config_dir=str(tmp_path / "config"),
            plugin_dir=str(tmp_path / "plugins"),
            output_dir=str(tmp_path / "output"),
        )

    assert exc.value.error_code == CONFIG_ERROR

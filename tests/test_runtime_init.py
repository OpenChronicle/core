from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from openchronicle.core.domain.errors.error_codes import CONFIG_ERROR
from tests.helpers.subprocess_env import build_env, run_oc_module


def _run_init(env: dict[str, str], *extra_args: str) -> dict[str, Any]:
    result = run_oc_module(["init", "--json", *extra_args], env=env)
    return cast(dict[str, Any], json.loads(result.stdout.strip()))


def test_oc_init_idempotent(tmp_path: Path) -> None:
    env = build_env(
        tmp_path,
        db_name="runtime.db",
        ensure_dirs=False,
        extra_env={
            "OC_DB_PATH": str(tmp_path / "data" / "runtime.db"),
            "OC_CONFIG_DIR": str(tmp_path / "config"),
            "OC_PLUGIN_DIR": str(tmp_path / "plugins"),
            "OC_OUTPUT_DIR": str(tmp_path / "output"),
        },
    )

    first = _run_init(env)
    assert first["status"] == "ok"

    second = _run_init(env)
    assert second["status"] == "ok"
    assert second["templates"]["model_config"]["status"] == "exists"
    assert second["templates"]["router_assist_model"]["status"] == "exists"


def test_oc_init_force_overwrites_templates(tmp_path: Path) -> None:
    env = build_env(
        tmp_path,
        db_name="runtime_force.db",
        ensure_dirs=False,
    )

    first = _run_init(env)
    assert first["status"] == "ok"

    model_path = Path(first["templates"]["model_config"]["path"])
    original_content = model_path.read_text(encoding="utf-8")

    model_path.write_text("overwritten", encoding="utf-8")

    forced = _run_init(env, "--force")
    assert forced["templates"]["model_config"]["status"] == "overwritten"
    assert model_path.read_text(encoding="utf-8") == original_content


def test_missing_config_dir_errors_then_init_succeeds(tmp_path: Path) -> None:
    env = build_env(
        tmp_path,
        db_name="missing.db",
        ensure_dirs=False,
        extra_env={"OC_CONFIG_DIR": str(tmp_path / "missing_config")},
    )

    request = json.dumps({"protocol_version": "1", "command": "system.health", "args": {}})
    result = run_oc_module(["rpc", "--request", request], env=env)
    payload = cast(dict[str, Any], json.loads(result.stdout.strip()))

    assert payload["ok"] is False
    error = cast(dict[str, Any], payload["error"])
    assert error["error_code"] == CONFIG_ERROR

    init_payload = _run_init(env)
    assert init_payload["status"] == "ok"
    assert Path(env["OC_CONFIG_DIR"]).exists()

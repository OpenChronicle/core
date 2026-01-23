from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "health.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    return env


def _run_rpc(request: dict[str, object], *, env: dict[str, str]) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "openchronicle.interfaces.cli.main",
            "rpc",
            "--request",
            json.dumps(request),
        ],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    return cast(dict[str, Any], json.loads(result.stdout.strip()))


def test_rpc_system_health_ok(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    payload = _run_rpc({"protocol_version": "1", "command": "system.health", "args": {}}, env=env)
    assert payload["ok"] is True
    result = cast(dict[str, Any], payload["result"])
    assert result["ok"] is True

    storage = cast(dict[str, Any], result["storage"])
    assert storage["type"] == "sqlite"
    assert storage["reachable"] is True

    config = cast(dict[str, Any], result["config"])
    assert isinstance(config["config_dir"], str)
    pools = cast(list[str], config["pools"])
    assert pools == sorted(pools)


def test_rpc_system_health_nsfw_unset(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    env.pop("OC_LLM_POOL_NSFW", None)
    payload = _run_rpc({"protocol_version": "1", "command": "system.health", "args": {}}, env=env)
    assert payload["ok"] is True
    result = cast(dict[str, Any], payload["result"])
    config = cast(dict[str, Any], result["config"])
    assert isinstance(config["nsfw_pool_configured"], bool)
    assert config["nsfw_pool_configured"] is False


def test_system_commands_includes_health(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    payload = _run_rpc({"protocol_version": "1", "command": "system.commands", "args": {}}, env=env)
    assert payload["ok"] is True
    result = cast(dict[str, Any], payload["result"])
    commands = cast(list[str], result["commands"])
    assert "system.health" in commands

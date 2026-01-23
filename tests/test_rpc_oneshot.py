from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "rpc.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    return env


def _run_rpc(
    args: list[str], *, input_text: str | None = None, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "openchronicle.interfaces.cli.main", "rpc", *args],
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_rpc_ping_request_arg(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"protocol_version": "1", "command": "system.ping", "args": {}})
    result = _run_rpc(["--request", request], env=env)
    assert result.returncode == 0

    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is True
    assert payload["result"] == {"pong": True}
    assert payload["protocol_version"] == "1"


def test_rpc_ping_stdin(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"protocol_version": "1", "command": "system.ping", "args": {}})
    result = _run_rpc([], input_text=request + "\n", env=env)
    assert result.returncode == 0

    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is True
    assert payload["result"] == {"pong": True}
    assert payload["protocol_version"] == "1"


def test_rpc_invalid_json(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    result = _run_rpc(["--request", "{not json"], env=env)
    assert result.returncode == 0

    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is False
    error = payload["error"]
    assert error["error_code"] == "INVALID_JSON"
    assert "details" in error


def test_rpc_invalid_request(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"protocol_version": "1", "args": {}})
    result = _run_rpc(["--request", request], env=env)
    assert result.returncode == 0

    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is False
    error = payload["error"]
    assert error["error_code"] == "INVALID_REQUEST"
    assert "details" in error


def test_rpc_unsupported_protocol_version(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"protocol_version": "999", "command": "system.ping", "args": {}})
    result = _run_rpc(["--request", request], env=env)
    assert result.returncode == 0

    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is False
    error = payload["error"]
    assert error["error_code"] == "UNSUPPORTED_PROTOCOL_VERSION"
    assert "details" in error

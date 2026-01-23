from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "negotiation.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    return env


def test_rpc_supported_protocol_version(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"protocol_version": "1", "command": "system.ping", "args": {}})
    result = subprocess.run(
        [sys.executable, "-m", "openchronicle.interfaces.cli.main", "rpc", "--request", request],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0

    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is True
    assert payload["protocol_version"] == "1"


def test_rpc_unsupported_protocol_version(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"protocol_version": "999", "command": "system.ping", "args": {}})
    result = subprocess.run(
        [sys.executable, "-m", "openchronicle.interfaces.cli.main", "rpc", "--request", request],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0

    payload = json.loads(result.stdout.strip())
    assert payload["ok"] is False
    error = payload["error"]
    assert error["error_code"] == "UNSUPPORTED_PROTOCOL_VERSION"
    assert "details" in error


def test_serve_unsupported_protocol_version(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    proc = subprocess.Popen(
        [sys.executable, "-m", "openchronicle.interfaces.cli.main", "serve"],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None

    bad_request = json.dumps({"protocol_version": "999", "command": "system.ping", "args": {}})
    shutdown = json.dumps({"protocol_version": "1", "command": "system.shutdown", "args": {}})

    proc.stdin.write(bad_request + "\n")
    proc.stdin.flush()
    line1 = proc.stdout.readline()

    proc.stdin.write(shutdown + "\n")
    proc.stdin.flush()
    line2 = proc.stdout.readline()
    proc.stdin.close()

    payload1 = json.loads(line1.strip())
    assert payload1["ok"] is False
    error = payload1["error"]
    assert error["error_code"] == "UNSUPPORTED_PROTOCOL_VERSION"
    assert "details" in error

    payload2 = json.loads(line2.strip())
    assert payload2["ok"] is True
    assert payload2["protocol_version"] == "1"

    proc.wait(timeout=5)

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "request_id.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    return env


def test_rpc_request_id_echo(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"command": "system.ping", "request_id": "abc", "args": {}})
    result = subprocess.run(
        [sys.executable, "-m", "openchronicle.interfaces.cli.main", "rpc", "--request", request],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0

    payload = cast(dict[str, Any], json.loads(result.stdout.strip()))
    assert payload["ok"] is True
    assert payload["request_id"] == "abc"


def test_serve_request_id_dedupe(tmp_path: Path) -> None:
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

    request = json.dumps({"protocol_version": "1", "command": "system.ping", "args": {}, "request_id": "dup1"})
    shutdown = json.dumps({"protocol_version": "1", "command": "system.shutdown", "args": {}})

    proc.stdin.write(request + "\n")
    proc.stdin.flush()
    line1 = proc.stdout.readline().strip()

    proc.stdin.write(request + "\n")
    proc.stdin.flush()
    line2 = proc.stdout.readline().strip()

    proc.stdin.write(shutdown + "\n")
    proc.stdin.flush()
    proc.stdout.readline()
    proc.stdin.close()

    assert line1
    assert line2
    assert line2 == line1

    proc.wait(timeout=5)


def test_rpc_invalid_request_id(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"command": "system.ping", "request_id": 123, "args": {}})
    result = subprocess.run(
        [sys.executable, "-m", "openchronicle.interfaces.cli.main", "rpc", "--request", request],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0

    payload = cast(dict[str, Any], json.loads(result.stdout.strip()))
    assert payload["ok"] is False
    error = cast(dict[str, Any], payload["error"])
    assert error["error_code"] == "INVALID_REQUEST"

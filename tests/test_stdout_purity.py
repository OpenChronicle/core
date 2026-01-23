from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "purity.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    return env


def test_rpc_stdout_purity(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    request = json.dumps({"command": "system.ping", "args": {}})
    result = subprocess.run(
        [sys.executable, "-m", "openchronicle.interfaces.cli.main", "rpc", "--request", request],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["ok"] is True
    assert payload["result"] == {"pong": True}


def test_serve_stdout_purity(tmp_path: Path) -> None:
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

    ping = json.dumps({"command": "system.ping", "args": {}})
    shutdown = json.dumps({"command": "system.shutdown", "args": {}})

    proc.stdin.write(ping + "\n")
    proc.stdin.flush()
    line1 = proc.stdout.readline()

    proc.stdin.write(shutdown + "\n")
    proc.stdin.flush()
    line2 = proc.stdout.readline()
    proc.stdin.close()

    payload1 = json.loads(line1.strip())
    payload2 = json.loads(line2.strip())
    assert payload1["ok"] is True
    assert payload2["ok"] is True

    proc.wait(timeout=5)
    remaining = proc.stdout.read()
    assert remaining.strip() == ""

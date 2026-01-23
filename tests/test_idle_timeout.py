from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _serve_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "idle.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    return env


def test_serve_idle_timeout_exits(tmp_path: Path) -> None:
    env = _serve_env(tmp_path)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "openchronicle.interfaces.cli.main",
            "serve",
            "--idle-timeout-seconds",
            "1",
        ],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        stdout, _stderr = proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)
        raise AssertionError("serve did not exit on idle timeout")

    assert proc.returncode == 0
    assert stdout.strip() == ""


def test_serve_idle_timeout_activity(tmp_path: Path) -> None:
    env = _serve_env(tmp_path)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "openchronicle.interfaces.cli.main",
            "serve",
            "--idle-timeout-seconds",
            "1",
        ],
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
    assert line1.strip()

    proc.stdin.write(shutdown + "\n")
    proc.stdin.flush()
    line2 = proc.stdout.readline()
    assert line2.strip()
    proc.stdin.close()

    proc.wait(timeout=5)

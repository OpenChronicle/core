from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "privacy_preview.db")
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


def test_privacy_preview_detects_email(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    payload = _run_rpc(
        {
            "command": "privacy.preview",
            "args": {
                "text": "contact a@b.com",
                "provider": "openai",
                "mode_override": "warn",
                "categories_override": ["email"],
            },
        },
        env=env,
    )
    assert payload["ok"] is True
    report = cast(dict[str, Any], payload["result"])["report"]
    assert report["categories"] == ["email"]
    assert report["counts"]["email"] == 1


def test_privacy_preview_redacts(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    payload = _run_rpc(
        {
            "command": "privacy.preview",
            "args": {
                "text": "contact a@b.com",
                "provider": "openai",
                "mode_override": "redact",
                "categories_override": ["email"],
            },
        },
        env=env,
    )
    assert payload["ok"] is True
    result = cast(dict[str, Any], payload["result"])
    assert "redacted_text" in result
    assert "[REDACTED_EMAIL]" in result["redacted_text"]
    assert "a@b.com" not in result["redacted_text"]


def test_privacy_preview_external_only_local_provider(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    payload = _run_rpc(
        {
            "command": "privacy.preview",
            "args": {
                "text": "contact a@b.com",
                "provider": "ollama",
                "mode_override": "block",
                "external_only_override": True,
                "categories_override": ["email"],
            },
        },
        env=env,
    )
    assert payload["ok"] is True
    result = cast(dict[str, Any], payload["result"])
    assert result["effective_policy"]["applies"] is False
    assert "redacted_text" not in result


def test_privacy_preview_invalid_override(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    payload = _run_rpc(
        {
            "command": "privacy.preview",
            "args": {
                "text": "contact a@b.com",
                "categories_override": "email",
            },
        },
        env=env,
    )
    assert payload["ok"] is False
    error = cast(dict[str, Any], payload["error"])
    assert error["error_code"] == "INVALID_ARGUMENT"

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from openchronicle.core.application.use_cases import convo_mode, create_conversation
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "errors.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    env["OC_LLM_PROVIDER"] = "stub"
    env["OC_LLM_FAST_POOL"] = ""
    env["OC_LLM_QUALITY_POOL"] = ""
    env.pop("OC_LLM_POOL_NSFW", None)
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


def test_error_normalization_invalid_request(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    payload = _run_rpc({"args": {}}, env=env)
    assert payload["ok"] is False
    error = cast(dict[str, Any], payload["error"])
    assert set(error.keys()) == {"error_code", "message", "hint", "details"}
    assert error["error_code"] == "INVALID_REQUEST"


def test_error_normalization_provider_error(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    db_path = Path(env["OC_DB_PATH"])
    storage = SqliteStore(str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)

    conversation = create_conversation.execute(
        storage=storage,
        convo_store=storage,
        emit_event=event_logger.append,
        title="NSFW",
    )
    convo_mode.set_mode(storage, conversation.id, mode="persona")

    payload = _run_rpc(
        {
            "command": "convo.ask",
            "args": {
                "conversation_id": conversation.id,
                "prompt": "roleplay explicit sex scene",
            },
        },
        env=env,
    )
    assert payload["ok"] is False
    error = cast(dict[str, Any], payload["error"])
    assert error["error_code"] == "NSFW_POOL_NOT_CONFIGURED"
    assert isinstance(error.get("details"), dict)
    assert "config_dir" in error["details"]


def test_error_normalization_invalid_argument(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    db_path = Path(env["OC_DB_PATH"])
    storage = SqliteStore(str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)

    conversation = create_conversation.execute(
        storage=storage,
        convo_store=storage,
        emit_event=event_logger.append,
        title="Mode",
    )

    payload = _run_rpc(
        {
            "command": "convo.mode",
            "args": {
                "conversation_id": conversation.id,
                "mode": "notamode",
            },
        },
        env=env,
    )
    assert payload["ok"] is False
    error = cast(dict[str, Any], payload["error"])
    assert error["error_code"] == "INVALID_ARGUMENT"
    assert "details" in error

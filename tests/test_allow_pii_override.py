from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from openchronicle.core.application.use_cases import create_conversation
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "allow_pii.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    env["OC_LLM_PROVIDER"] = "stub"
    env["OC_PRIVACY_OUTBOUND_MODE"] = "block"
    env["OC_PRIVACY_OUTBOUND_EXTERNAL_ONLY"] = "0"
    return env


def _prepare_conversation(db_path: Path) -> str:
    storage = SqliteStore(str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)
    conversation = create_conversation.execute(
        storage=storage,
        convo_store=storage,
        emit_event=event_logger.append,
        title="Allow PII",
    )
    return conversation.id


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


def test_allow_pii_override_blocks_without_flag(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    conversation_id = _prepare_conversation(Path(env["OC_DB_PATH"]))

    payload = _run_rpc(
        {
            "command": "convo.ask",
            "args": {
                "conversation_id": conversation_id,
                "prompt": "email me at user@example.com",
            },
        },
        env=env,
    )
    assert payload["ok"] is False
    error = cast(dict[str, Any], payload["error"])
    assert error["error_code"] == "OUTBOUND_PII_BLOCKED"


def test_allow_pii_override_succeeds(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    conversation_id = _prepare_conversation(Path(env["OC_DB_PATH"]))

    payload = _run_rpc(
        {
            "command": "convo.ask",
            "args": {
                "conversation_id": conversation_id,
                "prompt": "email me at user@example.com",
                "allow_pii": True,
            },
        },
        env=env,
    )
    assert payload["ok"] is True

    storage = SqliteStore(str(env["OC_DB_PATH"]))
    events = storage.list_events(task_id=conversation_id)
    assert any(event.type == "privacy.override_used" for event in events)


def test_ask_async_persists_allow_pii(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    conversation_id = _prepare_conversation(Path(env["OC_DB_PATH"]))

    payload = _run_rpc(
        {
            "command": "convo.ask_async",
            "args": {
                "conversation_id": conversation_id,
                "prompt": "hello",
                "allow_pii": True,
            },
        },
        env=env,
    )
    assert payload["ok"] is True
    result = cast(dict[str, Any], payload["result"])
    task_id = cast(str, result["task_id"])

    storage = SqliteStore(str(env["OC_DB_PATH"]))
    task = storage.get_task(task_id)
    assert task is not None
    assert task.payload.get("allow_pii") is True

    events = storage.list_events(task_id=task_id)
    assert any(event.payload.get("allow_pii") is True for event in events)

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
from openchronicle.core.infrastructure.privacy.rule_privacy import RulePrivacyGate


def test_privacy_gate_detects_email_and_phone() -> None:
    gate = RulePrivacyGate()
    text = "Contact me at user@example.com or +1-415-555-1212."
    redacted, report = gate.analyze_and_apply(
        text=text,
        mode="warn",
        redact_style="mask",
        categories=["email", "phone"],
    )

    assert redacted == text
    assert report.action == "warn"
    assert report.counts == {"email": 1, "phone": 1}
    assert report.categories == ["email", "phone"]


def test_privacy_gate_redacts() -> None:
    gate = RulePrivacyGate()
    text = "Email me at person@example.com."
    redacted, report = gate.analyze_and_apply(
        text=text,
        mode="redact",
        redact_style="mask",
        categories=["email"],
    )

    assert "[REDACTED_EMAIL]" in redacted
    assert report.redactions_applied is True


def _rpc_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OC_DB_PATH"] = str(tmp_path / "privacy.db")
    env["OC_CONFIG_DIR"] = str(tmp_path / "config")
    env["OC_PLUGIN_DIR"] = str(tmp_path / "plugins")
    env["OC_OUTPUT_DIR"] = str(tmp_path / "output")
    env["OC_LLM_PROVIDER"] = "openai"
    env["OC_PRIVACY_OUTBOUND_MODE"] = "block"
    env["OC_PRIVACY_OUTBOUND_EXTERNAL_ONLY"] = "1"
    return env


def _prepare_conversation(db_path: Path) -> str:
    storage = SqliteStore(str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)
    conversation = create_conversation.execute(
        storage=storage,
        convo_store=storage,
        emit_event=event_logger.append,
        title="Privacy",
    )
    return conversation.id


def test_privacy_gate_blocks_rpc(tmp_path: Path) -> None:
    env = _rpc_env(tmp_path)
    conversation_id = _prepare_conversation(Path(env["OC_DB_PATH"]))

    request = json.dumps(
        {
            "command": "convo.ask",
            "args": {
                "conversation_id": conversation_id,
                "prompt": "email me at user@example.com",
            },
        }
    )
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
    assert error["error_code"] == "OUTBOUND_PII_BLOCKED"
    details = cast(dict[str, Any], error["details"])
    assert details["categories"] == ["email"]

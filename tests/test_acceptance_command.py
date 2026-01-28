from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from tests.helpers.subprocess_env import build_env, run_oc_module


def test_acceptance_command_json(tmp_path: Path) -> None:
    env = build_env(
        tmp_path,
        db_name="acceptance.db",
        ensure_dirs=False,
        extra_env={
            "OC_ACCEPTANCE_PROVIDER": "stub",
            "OC_LLM_PROVIDER": "stub",
            "OC_LLM_FAST_POOL": "",
            "OC_LLM_QUALITY_POOL": "",
            "OC_LLM_POOL_NSFW": "",
        },
    )

    init_result = run_oc_module(["init", "--json"], env=env)
    assert init_result.returncode == 0

    result = run_oc_module(["acceptance", "--json"], env=env)
    assert result.returncode == 0

    payload = cast(dict[str, Any], json.loads(result.stdout.strip()))
    assert payload["status"] == "pass"
    assert isinstance(payload.get("health"), dict)
    assert payload.get("conversation_id")
    turn_ids = payload.get("turn_ids")
    assert isinstance(turn_ids, list)
    assert payload.get("export_verified") is True
    assert isinstance(payload.get("errors"), list)

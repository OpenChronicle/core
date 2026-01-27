from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from openchronicle.core.application.use_cases import selftest_run


def test_selftest_use_case(tmp_path: Path) -> None:
    result = selftest_run.execute(
        str(tmp_path / "selftest"),
        json_output=False,
        keep_artifacts=True,
        with_plugins=True,
    )

    assert result["ok"] is True
    assert result.get("conversation_id")
    assert result.get("turn_id")

    memory_ids = cast(list[str], result.get("memory_ids"))
    assert len(memory_ids) == 1

    export_path = Path(cast(str, result.get("export_path")))
    assert export_path.exists()

    plugin_result = cast(dict[str, Any], result.get("plugin_result"))
    assert plugin_result.get("ok") is True
    assert plugin_result.get("draft_preview")

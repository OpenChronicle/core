from __future__ import annotations

from openchronicle.interfaces.cli.stdio import RUNNABLE_TASK_TYPES


def test_runnable_task_types_guard() -> None:
    assert "plugin.invoke" in RUNNABLE_TASK_TYPES
    assert "convo.ask" in RUNNABLE_TASK_TYPES

    disallowed_handlers = {"hello.echo"}

    for task_type in RUNNABLE_TASK_TYPES:
        if task_type in {"plugin.invoke", "convo.ask"}:
            continue
        assert "." not in task_type
        assert task_type not in disallowed_handlers

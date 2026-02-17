"""CLI tests for scheduler commands."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from openchronicle.core.application.use_cases import create_project
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.cli.main import main


@pytest.fixture()
def _stub_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OC_LLM_PROVIDER", "stub")


@pytest.fixture()
def container(tmp_path: Path, _stub_env: None) -> Iterator[CoreContainer]:
    mp = pytest.MonkeyPatch()
    mp.setenv("OC_DB_PATH", str(tmp_path / "test.db"))
    c = CoreContainer()
    yield c
    mp.undo()


def _run(args: list[str], container: CoreContainer) -> tuple[int, str]:
    """Run a CLI command, return (rc, printed_output)."""
    with patch("builtins.print") as mock_print:
        with patch(
            "openchronicle.interfaces.cli.main._build_container",
            return_value=container,
        ):
            rc = main(args)
    output = "\n".join(str(c.args[0]) if c.args else "" for c in mock_print.call_args_list)
    return rc, output


class TestSchedulerAdd:
    def test_add_one_shot(self, container: CoreContainer) -> None:
        project = create_project.execute(container.orchestrator, "test")
        rc, out = _run(
            [
                "scheduler",
                "add",
                "--project-id",
                project.id,
                "--name",
                "nightly",
                "--task-type",
                "plugin.invoke",
                "--payload",
                '{"handler": "hello.echo"}',
            ],
            container,
        )
        assert rc == 0
        assert "Created job" in out

    def test_add_json(self, container: CoreContainer) -> None:
        project = create_project.execute(container.orchestrator, "test")
        rc, out = _run(
            [
                "scheduler",
                "add",
                "--project-id",
                project.id,
                "--name",
                "rec",
                "--task-type",
                "plugin.invoke",
                "--payload",
                "{}",
                "--interval",
                "300",
                "--json",
            ],
            container,
        )
        assert rc == 0
        payload = json.loads(out)
        assert payload["ok"] is True
        assert payload["result"]["interval_seconds"] == 300

    def test_add_invalid_payload(self, container: CoreContainer) -> None:
        rc, out = _run(
            [
                "scheduler",
                "add",
                "--project-id",
                "x",
                "--name",
                "j",
                "--task-type",
                "t",
                "--payload",
                "not-json",
            ],
            container,
        )
        assert rc == 1
        assert "invalid JSON" in out


class TestSchedulerList:
    def test_list_empty(self, container: CoreContainer) -> None:
        rc, out = _run(["scheduler", "list"], container)
        assert rc == 0
        assert "No scheduled jobs" in out

    def test_list_with_jobs(self, container: CoreContainer) -> None:
        project = create_project.execute(container.orchestrator, "test")
        container.scheduler.add_job(project.id, "j1", "t", {})
        rc, out = _run(["scheduler", "list"], container)
        assert rc == 0
        assert "j1" in out

    def test_list_json(self, container: CoreContainer) -> None:
        project = create_project.execute(container.orchestrator, "test")
        container.scheduler.add_job(project.id, "j1", "t", {})
        rc, out = _run(["scheduler", "list", "--json"], container)
        assert rc == 0
        payload = json.loads(out)
        assert payload["ok"] is True
        assert len(payload["result"]["jobs"]) == 1


class TestSchedulerTick:
    def test_tick_no_due(self, container: CoreContainer) -> None:
        rc, out = _run(["scheduler", "tick"], container)
        assert rc == 0
        assert "No jobs due" in out

    def test_tick_json(self, container: CoreContainer) -> None:
        rc, out = _run(["scheduler", "tick", "--json"], container)
        assert rc == 0
        payload = json.loads(out)
        assert payload["ok"] is True
        assert payload["result"]["jobs_fired"] == 0


class TestSchedulerPauseResumeCancel:
    def test_pause_and_resume(self, container: CoreContainer) -> None:
        project = create_project.execute(container.orchestrator, "test")
        job = container.scheduler.add_job(project.id, "j", "t", {})
        rc, out = _run(["scheduler", "pause", job.id], container)
        assert rc == 0
        assert "Paused" in out

        rc, out = _run(["scheduler", "resume", job.id], container)
        assert rc == 0
        assert "Resumed" in out

    def test_cancel(self, container: CoreContainer) -> None:
        project = create_project.execute(container.orchestrator, "test")
        job = container.scheduler.add_job(project.id, "j", "t", {})
        rc, out = _run(["scheduler", "cancel", job.id], container)
        assert rc == 0
        assert "Cancelled" in out

    def test_pause_missing(self, container: CoreContainer) -> None:
        rc, out = _run(["scheduler", "pause", "nonexistent"], container)
        assert rc == 1
        assert "not found" in out

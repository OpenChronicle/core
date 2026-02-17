"""Scheduler CLI commands: add/list/pause/resume/cancel/tick."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime

from openchronicle.core.application.services.scheduler import (
    InvalidTransitionError,
    JobNotFoundError,
)
from openchronicle.core.infrastructure.wiring.container import CoreContainer

from ._helpers import json_envelope, print_json


def cmd_scheduler(args: argparse.Namespace, container: CoreContainer) -> int:
    """Dispatch to scheduler subcommands."""
    dispatch: dict[str, Callable[[argparse.Namespace, CoreContainer], int]] = {
        "add": cmd_scheduler_add,
        "list": cmd_scheduler_list,
        "pause": cmd_scheduler_pause,
        "resume": cmd_scheduler_resume,
        "cancel": cmd_scheduler_cancel,
        "tick": cmd_scheduler_tick,
    }
    handler = dispatch.get(args.scheduler_command)
    if handler is None:
        print("Usage: oc scheduler {add|list|pause|resume|cancel|tick}")
        return 1
    return handler(args, container)


def cmd_scheduler_add(args: argparse.Namespace, container: CoreContainer) -> int:
    """Create a scheduled job."""
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON payload: {exc}")
        return 1

    due_at = None
    if args.due_at:
        try:
            due_at = datetime.fromisoformat(args.due_at)
        except ValueError:
            print(f"Error: invalid ISO datetime: {args.due_at}")
            return 1

    job = container.scheduler.add_job(
        project_id=args.project_id,
        name=args.name,
        task_type=args.task_type,
        task_payload=payload,
        due_at=due_at,
        interval_seconds=args.interval,
        max_failures=args.max_failures,
    )

    if args.json:
        print_json(
            json_envelope(
                command="scheduler.add",
                ok=True,
                result=_job_dict(job),
                error=None,
            )
        )
    else:
        print(f"Created job {job.id}")
        print(f"  name: {job.name}")
        print(f"  task_type: {job.task_type}")
        print(f"  next_due_at: {job.next_due_at.isoformat()}")
        if job.interval_seconds:
            print(f"  interval: {job.interval_seconds}s")
    return 0


def cmd_scheduler_list(args: argparse.Namespace, container: CoreContainer) -> int:
    """List scheduled jobs."""
    jobs = container.scheduler.list_jobs(
        project_id=getattr(args, "project_id", None),
        status=getattr(args, "status", None),
    )

    if args.json:
        print_json(
            json_envelope(
                command="scheduler.list",
                ok=True,
                result={"jobs": [_job_dict(j) for j in jobs]},
                error=None,
            )
        )
    else:
        if not jobs:
            print("No scheduled jobs.")
            return 0
        for j in jobs:
            interval = f"  every {j.interval_seconds}s" if j.interval_seconds else "  one-shot"
            print(f"  {j.id}  {j.status.value:<10} {j.name:<20} {interval}  due={j.next_due_at.isoformat()}")
    return 0


def cmd_scheduler_pause(args: argparse.Namespace, container: CoreContainer) -> int:
    """Pause a job."""
    try:
        job = container.scheduler.pause_job(args.job_id)
    except JobNotFoundError:
        print(f"Error: job not found: {args.job_id}")
        return 1
    except InvalidTransitionError as exc:
        print(f"Error: {exc}")
        return 1

    if args.json:
        print_json(json_envelope(command="scheduler.pause", ok=True, result=_job_dict(job), error=None))
    else:
        print(f"Paused job {job.id}")
    return 0


def cmd_scheduler_resume(args: argparse.Namespace, container: CoreContainer) -> int:
    """Resume a paused job."""
    try:
        job = container.scheduler.resume_job(args.job_id)
    except JobNotFoundError:
        print(f"Error: job not found: {args.job_id}")
        return 1
    except InvalidTransitionError as exc:
        print(f"Error: {exc}")
        return 1

    if args.json:
        print_json(json_envelope(command="scheduler.resume", ok=True, result=_job_dict(job), error=None))
    else:
        print(f"Resumed job {job.id}")
    return 0


def cmd_scheduler_cancel(args: argparse.Namespace, container: CoreContainer) -> int:
    """Cancel a job."""
    try:
        job = container.scheduler.cancel_job(args.job_id)
    except JobNotFoundError:
        print(f"Error: job not found: {args.job_id}")
        return 1
    except InvalidTransitionError as exc:
        print(f"Error: {exc}")
        return 1

    if args.json:
        print_json(json_envelope(command="scheduler.cancel", ok=True, result=_job_dict(job), error=None))
    else:
        print(f"Cancelled job {job.id}")
    return 0


def cmd_scheduler_tick(args: argparse.Namespace, container: CoreContainer) -> int:
    """Fire one scheduler tick."""
    now = datetime.now(UTC)
    results = container.scheduler.tick(now=now, max_jobs=args.max_jobs)

    if args.json:
        print_json(
            json_envelope(
                command="scheduler.tick",
                ok=True,
                result={
                    "jobs_fired": len(results),
                    "tasks": [{"job_id": job.id, "job_name": job.name, "task_id": task.id} for job, task in results],
                },
                error=None,
            )
        )
    else:
        if not results:
            print("No jobs due.")
        else:
            print(f"Fired {len(results)} job(s):")
            for job, task in results:
                print(f"  {job.name} -> task {task.id}")
    return 0


def _job_dict(job: object) -> dict[str, object]:
    """Convert a ScheduledJob to a serializable dict."""
    from openchronicle.core.domain.models.scheduled_job import ScheduledJob

    assert isinstance(job, ScheduledJob)
    return {
        "id": job.id,
        "project_id": job.project_id,
        "name": job.name,
        "task_type": job.task_type,
        "status": job.status.value,
        "next_due_at": job.next_due_at.isoformat(),
        "interval_seconds": job.interval_seconds,
        "fire_count": job.fire_count,
        "last_task_id": job.last_task_id,
        "created_at": job.created_at.isoformat(),
    }

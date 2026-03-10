"""Output CLI commands: output save/list/latest/cleanup."""

from __future__ import annotations

import argparse
import json

from openchronicle.core.domain.exceptions import ValidationError
from openchronicle.core.infrastructure.wiring.container import CoreContainer


def cmd_output(args: argparse.Namespace, container: CoreContainer) -> int:
    """Dispatch to output subcommands."""
    from collections.abc import Callable

    output_dispatch: dict[str, Callable[[argparse.Namespace, CoreContainer], int]] = {
        "save": cmd_output_save,
        "list": cmd_output_list,
        "latest": cmd_output_latest,
        "cleanup": cmd_output_cleanup,
    }
    handler = output_dispatch.get(args.output_command)
    if handler is None:
        print("Usage: oc output <save|list|latest|cleanup>")
        return 1
    return handler(args, container)


def cmd_output_save(args: argparse.Namespace, container: CoreContainer) -> int:
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}")
        return 1
    try:
        path = container.output_manager.save_report(args.report_type, data)
    except ValidationError as exc:
        print(str(exc))
        return 1
    print(str(path))
    return 0


def cmd_output_list(args: argparse.Namespace, container: CoreContainer) -> int:
    try:
        files = container.output_manager.list_outputs(args.report_type)
    except ValidationError as exc:
        print(str(exc))
        return 1
    for f in files:
        print(str(f))
    return 0


def cmd_output_latest(args: argparse.Namespace, container: CoreContainer) -> int:
    try:
        path = container.output_manager.latest_output(args.report_type)
    except ValidationError as exc:
        print(str(exc))
        return 1
    if path is None:
        print(f"No output found for: {args.report_type}")
        return 1
    print(str(path))
    return 0


def cmd_output_cleanup(args: argparse.Namespace, container: CoreContainer) -> int:
    try:
        deleted = container.output_manager.cleanup(args.max_age_days)
    except ValidationError as exc:
        print(str(exc))
        return 1
    print(f"Deleted {deleted} files")
    return 0

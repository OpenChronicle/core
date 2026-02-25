"""Webhook CLI commands: webhook register/list/delete/deliveries."""

from __future__ import annotations

import argparse

from openchronicle.core.application.use_cases import delete_webhook, list_webhooks, register_webhook
from openchronicle.core.domain.exceptions import NotFoundError
from openchronicle.core.infrastructure.wiring.container import CoreContainer


def cmd_webhook(args: argparse.Namespace, container: CoreContainer) -> int:
    """Dispatch to webhook subcommands."""
    from collections.abc import Callable

    webhook_dispatch: dict[str, Callable[[argparse.Namespace, CoreContainer], int]] = {
        "register": cmd_webhook_register,
        "list": cmd_webhook_list,
        "delete": cmd_webhook_delete,
        "deliveries": cmd_webhook_deliveries,
    }
    handler = webhook_dispatch.get(args.webhook_command)
    if handler is None:
        print("Usage: oc webhook <subcommand>")
        return 1
    return handler(args, container)


def cmd_webhook_register(args: argparse.Namespace, container: CoreContainer) -> int:
    sub = register_webhook.execute(
        webhook_service=container.webhook_service,
        emit_event=container.emit_event,
        project_id=args.project_id,
        url=args.url,
        event_filter=args.filter,
        description=args.description,
    )
    container.ensure_webhook_dispatcher()
    print(f"{sub.id}\t{sub.url}\t{sub.event_filter}")
    return 0


def cmd_webhook_list(args: argparse.Namespace, container: CoreContainer) -> int:
    subs = list_webhooks.execute(
        webhook_service=container.webhook_service,
        project_id=args.project_id,
        active_only=args.active_only,
    )
    for s in subs:
        status = "active" if s.active else "inactive"
        print(f"{s.id}\t{s.url}\t{s.event_filter}\t{status}\t{s.description}")
    return 0


def cmd_webhook_delete(args: argparse.Namespace, container: CoreContainer) -> int:
    try:
        delete_webhook.execute(
            webhook_service=container.webhook_service,
            emit_event=container.emit_event,
            subscription_id=args.webhook_id,
        )
    except NotFoundError as exc:
        print(str(exc))
        return 1
    print(f"Deleted: {args.webhook_id}")
    return 0


def cmd_webhook_deliveries(args: argparse.Namespace, container: CoreContainer) -> int:
    try:
        container.webhook_service.get(args.webhook_id)
    except NotFoundError as exc:
        print(str(exc))
        return 1
    deliveries = container.storage.list_deliveries(args.webhook_id, limit=args.limit)
    for d in deliveries:
        status = "ok" if d.success else "fail"
        code = str(d.status_code) if d.status_code is not None else "-"
        error = d.error_message or ""
        print(f"{d.id}\t{d.event_id}\t#{d.attempt_number}\t{code}\t{status}\t{error}")
    return 0

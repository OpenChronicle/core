"""Open WebUI management CLI commands.

Manage webui-mode conversations and print connection URLs for configuring
Open WebUI to use OC's persistent OpenAI-compatible API endpoints.
"""

from __future__ import annotations

import argparse
import os

from openchronicle.core.domain.models.conversation import Conversation
from openchronicle.core.domain.models.project import Event
from openchronicle.core.infrastructure.wiring.container import CoreContainer
from openchronicle.interfaces.api.config import HTTPConfig


def cmd_openwebui(args: argparse.Namespace, container: CoreContainer) -> int:
    """Dispatch to openwebui subcommands."""
    dispatch = {
        "new": cmd_openwebui_new,
        "url": cmd_openwebui_url,
        "list": cmd_openwebui_list,
    }
    handler = dispatch.get(args.openwebui_command)
    if handler is None:
        print("Usage: oc openwebui <new|url|list>")
        return 1
    return handler(args, container)


def _resolve_project_id(args: argparse.Namespace) -> str | None:
    """Resolve project ID from --project-id flag or OC_OPENWEBUI_PROJECT_ID env var."""
    pid: str | None = getattr(args, "project_id", None)
    if pid:
        return pid
    return os.environ.get("OC_OPENWEBUI_PROJECT_ID")


def _get_base_url() -> str:
    """Build the API base URL from HTTPConfig."""
    http_config = HTTPConfig.from_env()
    host = http_config.host
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    return f"http://{host}:{http_config.port}"


def cmd_openwebui_new(args: argparse.Namespace, container: CoreContainer) -> int:
    """Create a new webui conversation and print its URL."""
    project_id = _resolve_project_id(args)
    if not project_id:
        print("Error: --project-id required (or set OC_OPENWEBUI_PROJECT_ID env var)")
        return 1

    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found")
        return 1

    title = getattr(args, "title", None) or "Open WebUI Session"
    conversation = Conversation(
        project_id=project_id,
        title=title,
        mode="webui",
    )
    container.storage.add_conversation(conversation)
    container.emit_event(
        Event(
            project_id=project_id,
            task_id=conversation.id,
            type="convo.created",
            payload={
                "conversation_id": conversation.id,
                "title": conversation.title,
                "source": "cli:openwebui",
            },
        )
    )

    base_url = _get_base_url()
    url = f"{base_url}/v1/p/{project_id}/c/{conversation.id}"

    print(f"Created conversation: {conversation.id}")
    print(f"Title: {title}")
    print(f"Open WebUI base URL: {url}")

    return 0


def cmd_openwebui_url(args: argparse.Namespace, container: CoreContainer) -> int:
    """Print the project-scoped base URL for Open WebUI."""
    project_id = _resolve_project_id(args)
    if not project_id:
        print("Error: --project-id required (or set OC_OPENWEBUI_PROJECT_ID env var)")
        return 1

    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found")
        return 1

    base_url = _get_base_url()
    url = f"{base_url}/v1/p/{project_id}"

    print(f"Project: {project.name} ({project_id})")
    print(f"Open WebUI base URL: {url}")

    return 0


def cmd_openwebui_list(args: argparse.Namespace, container: CoreContainer) -> int:
    """List webui-mode conversations for a project."""
    project_id = _resolve_project_id(args)
    if not project_id:
        print("Error: --project-id required (or set OC_OPENWEBUI_PROJECT_ID env var)")
        return 1

    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found")
        return 1

    convos = container.storage.list_conversations(project_id=project_id)
    webui_convos = [c for c in convos if c.mode == "webui"]

    if not webui_convos:
        print("No webui conversations found.")
        print(f"Create one with: oc openwebui new --project-id {project_id}")
        return 0

    print(f"{'ID':<38} {'Title':<30} {'Created'}")
    print("-" * 90)
    for c in webui_convos:
        created = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "?"
        print(f"{c.id:<38} {(c.title or '(untitled)'):<30} {created}")

    return 0

from __future__ import annotations

from collections.abc import Callable

from openchronicle.core.application.use_cases import ask_conversation
from openchronicle.core.domain.models.project import Event, Task, TaskStatus
from openchronicle.core.domain.ports.conversation_store_port import ConversationStorePort
from openchronicle.core.domain.ports.interaction_router_port import InteractionRouterPort
from openchronicle.core.domain.ports.llm_port import LLMPort, LLMProviderError
from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort
from openchronicle.core.domain.ports.privacy_gate_port import PrivacyGatePort
from openchronicle.core.domain.ports.storage_port import StoragePort
from openchronicle.core.infrastructure.config.settings import PrivacyOutboundSettings


def _eligible_tasks(tasks: list[Task], task_type: str) -> list[Task]:
    eligible = [task for task in tasks if task.status == TaskStatus.PENDING and task.type == task_type]
    eligible.sort(key=lambda task: (task.created_at, task.id))
    return eligible


async def execute(
    *,
    storage: StoragePort,
    convo_store: ConversationStorePort,
    memory_store: MemoryStorePort,
    llm: LLMPort,
    interaction_router: InteractionRouterPort,
    emit_event: Callable[[Event], None],
    privacy_gate: PrivacyGatePort | None = None,
    privacy_settings: PrivacyOutboundSettings | None = None,
    task_type: str = "convo.ask",
) -> dict[str, object]:
    tasks: list[Task] = []
    for project in storage.list_projects():
        tasks.extend(storage.list_tasks_by_project(project.id))

    eligible = _eligible_tasks(tasks, task_type)
    if not eligible:
        return {
            "ran": False,
            "task_id": None,
            "status": "none",
            "conversation_id": None,
            "turn_id": None,
            "error": None,
        }

    task = eligible[0]
    storage.update_task_status(task.id, TaskStatus.RUNNING.value)
    emit_event(
        Event(
            project_id=task.project_id,
            task_id=task.id,
            type="task.started",
            payload={"task_id": task.id, "task_type": task.type},
        )
    )

    conversation_id = task.payload.get("conversation_id") if isinstance(task.payload, dict) else None
    prompt_text = task.payload.get("prompt") if isinstance(task.payload, dict) else None
    allow_pii = bool(task.payload.get("allow_pii", False)) if isinstance(task.payload, dict) else False

    try:
        if not isinstance(conversation_id, str) or not isinstance(prompt_text, str):
            raise ValueError("Task payload missing conversation_id or prompt")

        turn = await ask_conversation.execute(
            convo_store=convo_store,
            storage=storage,
            memory_store=memory_store,
            llm=llm,
            interaction_router=interaction_router,
            emit_event=emit_event,
            conversation_id=conversation_id,
            prompt_text=prompt_text,
            allow_pii=allow_pii,
            privacy_gate=privacy_gate,
            privacy_settings=privacy_settings,
        )

        storage.update_task_status(task.id, TaskStatus.COMPLETED.value)
        emit_event(
            Event(
                project_id=task.project_id,
                task_id=task.id,
                type="task.completed",
                payload={
                    "task_id": task.id,
                    "conversation_id": conversation_id,
                    "turn_id": turn.id,
                },
            )
        )
        return {
            "ran": True,
            "task_id": task.id,
            "status": "completed",
            "conversation_id": conversation_id,
            "turn_id": turn.id,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        error_code = None
        hint = None
        details = None
        message = "Task execution failed."
        if isinstance(exc, LLMProviderError):
            error_code = exc.error_code
            hint = exc.hint
            details = exc.details if isinstance(exc.details, dict) else None
            message = str(exc)
        elif isinstance(exc, ValueError):
            message = str(exc)
            error_code = "INVALID_ARGUMENT"

        storage.update_task_status(task.id, TaskStatus.FAILED.value)
        emit_event(
            Event(
                project_id=task.project_id,
                task_id=task.id,
                type="task.failed",
                payload={
                    "task_id": task.id,
                    "error_code": error_code,
                },
            )
        )
        return {
            "ran": True,
            "task_id": task.id,
            "status": "failed",
            "conversation_id": conversation_id if isinstance(conversation_id, str) else None,
            "turn_id": None,
            "error": {
                "error_code": error_code or "INTERNAL_ERROR",
                "message": message,
                "hint": hint,
                "details": details,
            },
        }

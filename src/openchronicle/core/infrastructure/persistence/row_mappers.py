"""Pure data mappers: sqlite3.Row → domain model."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from openchronicle.core.domain.models.asset import Asset, AssetLink
from openchronicle.core.domain.models.conversation import Conversation, Turn
from openchronicle.core.domain.models.memory_item import MemoryItem
from openchronicle.core.domain.models.project import (
    Agent,
    Event,
    LLMUsage,
    Project,
    Span,
    SpanStatus,
    Task,
    TaskStatus,
)
from openchronicle.core.domain.models.scheduled_job import JobStatus, ScheduledJob


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def row_to_project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        name=row["name"],
        metadata=json.loads(row["metadata"] or "{}"),
        created_at=_parse_dt(row["created_at"]),
    )


def row_to_agent(row: sqlite3.Row) -> Agent:
    return Agent(
        id=row["id"],
        project_id=row["project_id"],
        role=row["role"],
        name=row["name"],
        provider=row["provider"],
        model=row["model"],
        tags=json.loads(row["tags"] or "[]"),
        created_at=_parse_dt(row["created_at"]),
    )


def row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        project_id=row["project_id"],
        agent_id=row["agent_id"],
        parent_task_id=row["parent_task_id"],
        type=row["type"],
        payload=json.loads(row["payload"] or "{}"),
        status=TaskStatus(row["status"]),
        result_json=row["result_json"],
        error_json=row["error_json"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def row_to_event(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        project_id=row["project_id"],
        task_id=row["task_id"],
        agent_id=row["agent_id"],
        type=row["type"],
        payload=json.loads(row["payload"] or "{}"),
        created_at=_parse_dt(row["created_at"]),
        prev_hash=row["prev_hash"],
        hash=row["hash"],
    )


def row_to_span(row: sqlite3.Row) -> Span:
    return Span(
        id=row["id"],
        task_id=row["task_id"],
        agent_id=row["agent_id"],
        name=row["name"],
        start_event_id=row["start_event_id"],
        end_event_id=row["end_event_id"],
        status=SpanStatus(row["status"]),
        created_at=_parse_dt(row["created_at"]),
        ended_at=_parse_dt(row["ended_at"]) if row["ended_at"] else None,
    )


def row_to_llm_usage(row: sqlite3.Row) -> LLMUsage:
    return LLMUsage(
        id=row["id"],
        created_at=_parse_dt(row["created_at"]),
        project_id=row["project_id"],
        task_id=row["task_id"],
        agent_id=row["agent_id"],
        provider=row["provider"],
        model=row["model"],
        request_id=row["request_id"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        total_tokens=row["total_tokens"],
        latency_ms=row["latency_ms"],
    )


def row_to_conversation(row: sqlite3.Row) -> Conversation:
    try:
        mode = row["mode"]
    except KeyError:
        mode = None
    return Conversation(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        mode=mode or "general",
        created_at=_parse_dt(row["created_at"]),
    )


def row_to_turn(row: sqlite3.Row) -> Turn:
    reasons_raw = row["routing_reasons"] or "[]"
    try:
        memory_raw = row["memory_written_ids"]
    except KeyError:
        memory_raw = "[]"
    try:
        memory_ids = json.loads(memory_raw) if memory_raw else []
    except json.JSONDecodeError:
        memory_ids = []
    if not isinstance(memory_ids, list):
        memory_ids = []
    return Turn(
        id=row["id"],
        conversation_id=row["conversation_id"],
        turn_index=row["turn_index"],
        user_text=row["user_text"],
        assistant_text=row["assistant_text"],
        provider=row["provider"],
        model=row["model"],
        routing_reasons=json.loads(reasons_raw) if reasons_raw else [],
        memory_written_ids=memory_ids,
        created_at=_parse_dt(row["created_at"]),
    )


def row_to_memory_item(row: sqlite3.Row) -> MemoryItem:
    tags_raw = row["tags"] or "[]"
    updated_at_raw = row["updated_at"]
    return MemoryItem(
        id=row["id"],
        content=row["content"],
        tags=json.loads(tags_raw) if tags_raw else [],
        created_at=_parse_dt(row["created_at"]),
        pinned=bool(row["pinned"]),
        conversation_id=row["conversation_id"],
        project_id=row["project_id"],
        source=row["source"],
        updated_at=_parse_dt(updated_at_raw) if updated_at_raw else None,
    )


def row_to_scheduled_job(row: sqlite3.Row) -> ScheduledJob:
    return ScheduledJob(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        task_type=row["task_type"],
        task_payload=json.loads(row["task_payload"] or "{}"),
        status=JobStatus(row["status"]),
        next_due_at=_parse_dt(row["next_due_at"]),
        interval_seconds=row["interval_seconds"],
        cron_expr=row["cron_expr"],
        fire_count=row["fire_count"],
        consecutive_failures=row["consecutive_failures"],
        max_failures=row["max_failures"],
        last_fired_at=_parse_dt(row["last_fired_at"]) if row["last_fired_at"] else None,
        last_task_id=row["last_task_id"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def row_to_asset(row: sqlite3.Row) -> Asset:
    return Asset(
        id=row["id"],
        project_id=row["project_id"],
        filename=row["filename"],
        mime_type=row["mime_type"],
        file_path=row["file_path"],
        size_bytes=row["size_bytes"],
        content_hash=row["content_hash"],
        metadata=json.loads(row["metadata"] or "{}"),
        created_at=_parse_dt(row["created_at"]),
    )


def row_to_asset_link(row: sqlite3.Row) -> AssetLink:
    return AssetLink(
        id=row["id"],
        asset_id=row["asset_id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        role=row["role"],
        created_at=_parse_dt(row["created_at"]),
    )

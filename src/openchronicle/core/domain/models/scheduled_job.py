from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(UTC)


class JobStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    name: str = ""
    task_type: str = ""
    task_payload: dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.ACTIVE
    next_due_at: datetime = field(default_factory=_utc_now)
    interval_seconds: int | None = None
    cron_expr: str | None = None
    fire_count: int = 0
    consecutive_failures: int = 0
    max_failures: int = 0
    last_fired_at: datetime | None = None
    last_task_id: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

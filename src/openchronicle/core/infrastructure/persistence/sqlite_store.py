from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from openchronicle.core.domain.models.project import (
    Agent,
    Event,
    LLMUsage,
    Project,
    Resource,
    Span,
    SpanStatus,
    Task,
    TaskStatus,
)
from openchronicle.core.domain.ports.storage_port import StoragePort
from openchronicle.core.infrastructure.persistence import schema


class SqliteStore(StoragePort):
    def __init__(self, db_path: str = "data/openchronicle.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._transaction_depth = 0
        self._configure_connection()

    def init_schema(self) -> None:
        cur = self._conn.cursor()
        for stmt in schema.ALL_TABLES:
            cur.execute(stmt)
        self._commit_if_needed()
        self._ensure_parent_task_column()
        self._ensure_task_result_columns()
        self._ensure_indexes()
        # Ensure crash recovery runs even for reused databases
        self.recover_stale_tasks()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for SQLite transactions with savepoint nesting."""

        is_outer = self._transaction_depth == 0
        savepoint_name = None

        if is_outer:
            self._conn.execute("BEGIN")
        else:
            savepoint_name = f"sp_{self._transaction_depth + 1}"
            self._conn.execute(f"SAVEPOINT {savepoint_name}")

        self._transaction_depth += 1

        try:
            yield self._conn
            if is_outer:
                self._conn.commit()
            else:
                self._conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        except Exception:
            if is_outer:
                self._conn.rollback()
            else:
                self._conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                self._conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            raise
        finally:
            self._transaction_depth -= 1

    # Projects
    def add_project(self, project: Project) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO projects (id, name, metadata, created_at) VALUES (?, ?, ?, ?)",
            (project.id, project.name, json.dumps(project.metadata), project.created_at.isoformat()),
        )
        self._commit_if_needed()

    def list_projects(self) -> list[Project]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [self._row_to_project(r) for r in rows]

    def get_project(self, project_id: str) -> Project | None:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        return self._row_to_project(row) if row else None

    # Agents
    def add_agent(self, agent: Agent) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO agents (id, project_id, role, name, provider, model, tags, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                agent.id,
                agent.project_id,
                agent.role,
                agent.name,
                agent.provider,
                agent.model,
                json.dumps(agent.tags),
                agent.created_at.isoformat(),
            ),
        )
        self._commit_if_needed()

    def get_agent(self, agent_id: str) -> Agent | None:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
        return self._row_to_agent(row) if row else None

    def list_agents(self, project_id: str) -> list[Agent]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT * FROM agents WHERE project_id=? ORDER BY created_at ASC, id ASC", (project_id,)
        ).fetchall()
        return [self._row_to_agent(r) for r in rows]

    # Tasks
    def add_task(self, task: Task) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO tasks (id, project_id, agent_id, parent_task_id, type, payload, status, result_json, error_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.project_id,
                task.agent_id,
                task.parent_task_id,
                task.type,
                json.dumps(task.payload),
                task.status.value,
                task.result_json,
                task.error_json,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
            ),
        )
        self._commit_if_needed()

    def update_task_status(self, task_id: str, status: str) -> None:
        cur = self._conn.cursor()
        updated_at = datetime.now(UTC).isoformat()
        cur.execute(
            "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
            (status, updated_at, task_id),
        )
        self._commit_if_needed()

    def update_task_result(self, task_id: str, result_json: str, status: str) -> None:
        cur = self._conn.cursor()
        updated_at = datetime.now(UTC).isoformat()
        cur.execute(
            "UPDATE tasks SET result_json=?, status=?, updated_at=? WHERE id=?",
            (result_json, status, updated_at, task_id),
        )
        self._commit_if_needed()

    def update_task_error(self, task_id: str, error_json: str, status: str) -> None:
        cur = self._conn.cursor()
        updated_at = datetime.now(UTC).isoformat()
        cur.execute(
            "UPDATE tasks SET error_json=?, status=?, updated_at=? WHERE id=?",
            (error_json, status, updated_at, task_id),
        )
        self._commit_if_needed()

    def get_task(self, task_id: str) -> Task | None:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks_by_project(self, project_id: str) -> list[Task]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT * FROM tasks WHERE project_id=? ORDER BY created_at ASC, id ASC",
            (project_id,),
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    # Events
    def append_event(self, event: Event) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO events (id, project_id, task_id, agent_id, type, payload, created_at, prev_hash, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.project_id,
                event.task_id,
                event.agent_id,
                event.type,
                json.dumps(event.payload),
                event.created_at.isoformat(),
                event.prev_hash,
                event.hash,
            ),
        )
        self._commit_if_needed()

    def list_events(self, task_id: str) -> list[Event]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT * FROM events WHERE task_id=? ORDER BY created_at ASC, id ASC",
            (task_id,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    # Resources
    def add_resource(self, resource: Resource) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO resources (id, project_id, kind, path, content_hash, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                resource.id,
                resource.project_id,
                resource.kind,
                resource.path,
                resource.content_hash,
                json.dumps(resource.metadata),
                resource.created_at.isoformat(),
            ),
        )
        self._commit_if_needed()

    def list_resources(self, project_id: str) -> list[Resource]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM resources WHERE project_id=?", (project_id,)).fetchall()
        return [self._row_to_resource(r) for r in rows]

    # Spans
    def add_span(self, span: Span) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO spans
            (id, task_id, agent_id, name, start_event_id, end_event_id, status, created_at, ended_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                span.id,
                span.task_id,
                span.agent_id,
                span.name,
                span.start_event_id,
                span.end_event_id,
                span.status.value,
                span.created_at.isoformat(),
                span.ended_at.isoformat() if span.ended_at else None,
            ),
        )
        self._commit_if_needed()

    def update_span(self, span: Span) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """UPDATE spans
            SET end_event_id=?, status=?, ended_at=?
            WHERE id=?""",
            (
                span.end_event_id,
                span.status.value,
                span.ended_at.isoformat() if span.ended_at else None,
                span.id,
            ),
        )
        self._commit_if_needed()

    def list_spans(self, task_id: str) -> list[Span]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM spans WHERE task_id=? ORDER BY created_at ASC", (task_id,)).fetchall()
        return [self._row_to_span(r) for r in rows]

    def get_span(self, span_id: str) -> Span | None:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM spans WHERE id=?", (span_id,)).fetchone()
        return self._row_to_span(row) if row else None

    # ---- helpers ----
    def _row_to_project(self, row: sqlite3.Row) -> Project:
        return Project(
            id=row["id"],
            name=row["name"],
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=self._parse_dt(row["created_at"]),
        )

    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        return Agent(
            id=row["id"],
            project_id=row["project_id"],
            role=row["role"],
            name=row["name"],
            provider=row["provider"],
            model=row["model"],
            tags=json.loads(row["tags"] or "[]"),
            created_at=self._parse_dt(row["created_at"]),
        )

    def _row_to_task(self, row: sqlite3.Row) -> Task:
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
            created_at=self._parse_dt(row["created_at"]),
            updated_at=self._parse_dt(row["updated_at"]),
        )

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            project_id=row["project_id"],
            task_id=row["task_id"],
            agent_id=row["agent_id"],
            type=row["type"],
            payload=json.loads(row["payload"] or "{}"),
            created_at=self._parse_dt(row["created_at"]),
            prev_hash=row["prev_hash"],
            hash=row["hash"],
        )

    def _row_to_resource(self, row: sqlite3.Row) -> Resource:
        return Resource(
            id=row["id"],
            project_id=row["project_id"],
            kind=row["kind"],
            path=row["path"],
            content_hash=row["content_hash"],
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=self._parse_dt(row["created_at"]),
        )

    def _row_to_span(self, row: sqlite3.Row) -> Span:
        return Span(
            id=row["id"],
            task_id=row["task_id"],
            agent_id=row["agent_id"],
            name=row["name"],
            start_event_id=row["start_event_id"],
            end_event_id=row["end_event_id"],
            status=SpanStatus(row["status"]),
            created_at=self._parse_dt(row["created_at"]),
            ended_at=self._parse_dt(row["ended_at"]) if row["ended_at"] else None,
        )

    def _row_to_llm_usage(self, row: sqlite3.Row) -> LLMUsage:
        return LLMUsage(
            id=row["id"],
            created_at=self._parse_dt(row["created_at"]),
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

    def _parse_dt(self, value: str) -> datetime:
        return datetime.fromisoformat(value)

    def _configure_connection(self) -> None:
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA journal_mode = WAL;")
        self._conn.execute("PRAGMA synchronous = NORMAL;")
        self._conn.execute("PRAGMA busy_timeout = 5000;")

    def _commit_if_needed(self) -> None:
        if self._transaction_depth == 0:
            self._conn.commit()

    def _ensure_parent_task_column(self) -> None:
        cur = self._conn.cursor()
        columns = [row[1] for row in cur.execute("PRAGMA table_info(tasks)").fetchall()]
        if "parent_task_id" not in columns:
            cur.execute("ALTER TABLE tasks ADD COLUMN parent_task_id TEXT")
            self._commit_if_needed()

    def _ensure_task_result_columns(self) -> None:
        """Migrate existing databases to add result_json and error_json columns."""
        cur = self._conn.cursor()
        columns = [row[1] for row in cur.execute("PRAGMA table_info(tasks)").fetchall()]
        if "result_json" not in columns:
            cur.execute("ALTER TABLE tasks ADD COLUMN result_json TEXT")
        if "error_json" not in columns:
            cur.execute("ALTER TABLE tasks ADD COLUMN error_json TEXT")
        self._commit_if_needed()

    def _ensure_indexes(self) -> None:
        """Create indexes for query performance optimization."""
        cur = self._conn.cursor()
        for index_stmt in schema.INDEXES:
            cur.execute(index_stmt)
        self._commit_if_needed()

    def _append_event_with_hash(self, event: Event) -> None:
        existing = self.list_events(event.task_id) if event.task_id else []
        if existing:
            event.prev_hash = existing[-1].hash
        event.compute_hash()
        self.append_event(event)

    def recover_stale_tasks(self, emit_event: Callable[[Event], None] | None = None) -> list[str]:
        """Mark lingering running tasks as failed and close their spans."""

        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT * FROM tasks WHERE status=? ORDER BY created_at ASC, id ASC",
            (TaskStatus.RUNNING.value,),
        ).fetchall()

        recovered: list[str] = []
        for row in rows:
            task = self._row_to_task(row)
            failure_event = Event(
                project_id=task.project_id,
                task_id=task.id,
                agent_id=task.agent_id,
                type="task_failed",
                payload={
                    "reason": "crash_recovery",
                    "message": "Task marked failed after unexpected termination",
                },
            )

            with self.transaction():
                if emit_event:
                    emit_event(failure_event)
                else:
                    self._append_event_with_hash(failure_event)

                error_json = json.dumps(
                    {
                        "reason": "crash_recovery",
                        "message": "Task marked failed after unexpected termination",
                        "failed_event_id": failure_event.id,
                    }
                )
                updated_at = failure_event.created_at.isoformat()
                cur.execute(
                    "UPDATE tasks SET status=?, error_json=?, updated_at=? WHERE id=?",
                    (TaskStatus.FAILED.value, error_json, updated_at, task.id),
                )

                spans = self.list_spans(task.id)
                for span in spans:
                    if span.end_event_id is None or span.status == SpanStatus.STARTED:
                        span.status = SpanStatus.FAILED
                        span.end_event_id = failure_event.id
                        span.ended_at = failure_event.created_at
                        self.update_span(span)

                recovered.append(task.id)

        return recovered

    # LLM Usage
    def insert_llm_usage(self, usage: LLMUsage) -> None:
        """Record an LLM API call for usage tracking and budget enforcement."""
        cur = self._conn.cursor()
        # Handle both datetime and string created_at
        created_at_str = usage.created_at if isinstance(usage.created_at, str) else usage.created_at.isoformat()
        cur.execute(
            """
            INSERT INTO llm_usage (
                id, created_at, project_id, task_id, agent_id, provider, model,
                request_id, input_tokens, output_tokens, total_tokens, latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usage.id,
                created_at_str,
                usage.project_id,
                usage.task_id,
                usage.agent_id,
                usage.provider,
                usage.model,
                usage.request_id,
                usage.input_tokens,
                usage.output_tokens,
                usage.total_tokens,
                usage.latency_ms,
            ),
        )
        self._commit_if_needed()

    def list_llm_usage_by_project(self, project_id: str, limit: int | None = None, offset: int = 0) -> list[LLMUsage]:
        """List LLM usage records for a project, ordered by created_at DESC then id."""
        cur = self._conn.cursor()
        sql = """
            SELECT * FROM llm_usage
            WHERE project_id = ?
            ORDER BY created_at DESC, id DESC
        """
        params: list[str | int] = [project_id]

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        rows = cur.execute(sql, params).fetchall()
        return [self._row_to_llm_usage(r) for r in rows]

    def sum_tokens_by_task(self, task_id: str) -> dict[str, int]:
        """Sum token usage for a task. Returns dict with input/output/total counts."""
        cur = self._conn.cursor()
        row = cur.execute(
            """
            SELECT
                COALESCE(SUM(input_tokens), 0) as input,
                COALESCE(SUM(output_tokens), 0) as output,
                COALESCE(SUM(total_tokens), 0) as total
            FROM llm_usage
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()

        return {
            "input_tokens": row["input"],
            "output_tokens": row["output"],
            "total_tokens": row["total"],
        }

    def sum_tokens_by_project(self, project_id: str, since: str | None = None) -> dict[str, int]:
        """Sum token usage for a project with optional time window."""
        cur = self._conn.cursor()

        sql = """
            SELECT
                COALESCE(SUM(input_tokens), 0) as input,
                COALESCE(SUM(output_tokens), 0) as output,
                COALESCE(SUM(total_tokens), 0) as total
            FROM llm_usage
            WHERE project_id = ?
        """
        params: list[str] = [project_id]

        if since:
            sql += " AND created_at >= ?"
            params.append(since)

        row = cur.execute(sql, params).fetchone()

        return {
            "input_tokens": row["input"],
            "output_tokens": row["output"],
            "total_tokens": row["total"],
        }

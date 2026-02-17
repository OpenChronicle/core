"""Tests for time-since-last-interaction context injection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openchronicle.core.application.routing.router_policy import RouterPolicy
from openchronicle.core.application.use_cases.ask_conversation import prepare_ask
from openchronicle.core.domain.models.conversation import Conversation, Turn
from openchronicle.core.domain.models.project import Project
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore
from openchronicle.core.infrastructure.routing.rule_router import RuleInteractionRouter


def _setup(tmp_path: Path) -> tuple[SqliteStore, EventLogger, str]:
    db_path = tmp_path / "test.db"
    storage = SqliteStore(str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)
    project = Project(name="test-project")
    storage.add_project(project)
    return storage, event_logger, project.id


class TestTimeContextFirstTurn:
    """First turn in a conversation — no prior turns, uses conversation.created_at."""

    @pytest.mark.asyncio
    async def test_first_turn_uses_conversation_created_at(self, tmp_path: Path) -> None:
        storage, event_logger, project_id = _setup(tmp_path)

        convo = Conversation(
            project_id=project_id,
            title="Test",
            created_at=datetime.now(UTC) - timedelta(hours=2),
        )
        storage.add_conversation(convo)

        ctx = await prepare_ask(
            convo_store=storage,
            memory_store=storage,
            emit_event=event_logger.append,
            conversation_id=convo.id,
            prompt_text="Hello",
            interaction_router=RuleInteractionRouter(),
            router_policy=RouterPolicy(),
        )

        assert ctx.last_interaction_at == convo.created_at
        assert ctx.seconds_since_last_interaction is not None
        # ~2 hours = ~7200 seconds, allow some tolerance
        assert ctx.seconds_since_last_interaction >= 7190

    @pytest.mark.asyncio
    async def test_first_turn_has_time_system_message(self, tmp_path: Path) -> None:
        storage, event_logger, project_id = _setup(tmp_path)

        convo = Conversation(project_id=project_id, title="Test")
        storage.add_conversation(convo)

        ctx = await prepare_ask(
            convo_store=storage,
            memory_store=storage,
            emit_event=event_logger.append,
            conversation_id=convo.id,
            prompt_text="Hello",
            interaction_router=RuleInteractionRouter(),
            router_policy=RouterPolicy(),
        )

        time_msgs = [m for m in ctx.messages if m["role"] == "system" and "Last interaction:" in m["content"]]
        assert len(time_msgs) == 1
        assert "Current time:" in time_msgs[0]["content"]
        assert "Seconds since last interaction:" in time_msgs[0]["content"]


class TestTimeContextSubsequentTurn:
    """Subsequent turns — uses last turn's created_at."""

    @pytest.mark.asyncio
    async def test_uses_last_turn_timestamp(self, tmp_path: Path) -> None:
        storage, event_logger, project_id = _setup(tmp_path)

        convo = Conversation(
            project_id=project_id,
            title="Test",
            created_at=datetime.now(UTC) - timedelta(days=1),
        )
        storage.add_conversation(convo)

        # Add a turn from 30 minutes ago
        turn = Turn(
            conversation_id=convo.id,
            turn_index=1,
            user_text="Earlier question",
            assistant_text="Earlier answer",
            created_at=datetime.now(UTC) - timedelta(minutes=30),
        )
        storage.add_turn(turn)

        ctx = await prepare_ask(
            convo_store=storage,
            memory_store=storage,
            emit_event=event_logger.append,
            conversation_id=convo.id,
            prompt_text="Follow-up",
            interaction_router=RuleInteractionRouter(),
            router_policy=RouterPolicy(),
        )

        # Should reference the turn (30 min ago), not the conversation (1 day ago)
        assert ctx.last_interaction_at == turn.created_at
        assert ctx.seconds_since_last_interaction is not None
        assert ctx.seconds_since_last_interaction >= 1790  # ~30 min
        assert ctx.seconds_since_last_interaction < 7200  # definitely not 1 day


class TestTimeContextFormat:
    """Time context message format is machine-parseable."""

    @pytest.mark.asyncio
    async def test_message_contains_iso_timestamps(self, tmp_path: Path) -> None:
        storage, event_logger, project_id = _setup(tmp_path)

        convo = Conversation(project_id=project_id, title="Test")
        storage.add_conversation(convo)

        ctx = await prepare_ask(
            convo_store=storage,
            memory_store=storage,
            emit_event=event_logger.append,
            conversation_id=convo.id,
            prompt_text="Hello",
            interaction_router=RuleInteractionRouter(),
            router_policy=RouterPolicy(),
        )

        time_msgs = [m for m in ctx.messages if m["role"] == "system" and "Last interaction:" in m["content"]]
        content = time_msgs[0]["content"]

        # ISO format includes 'T' separator and '+' timezone
        assert "T" in content
        assert "+00:00" in content

    @pytest.mark.asyncio
    async def test_time_message_before_turn_history(self, tmp_path: Path) -> None:
        storage, event_logger, project_id = _setup(tmp_path)

        convo = Conversation(project_id=project_id, title="Test")
        storage.add_conversation(convo)

        turn = Turn(
            conversation_id=convo.id,
            turn_index=1,
            user_text="Prior question",
            assistant_text="Prior answer",
        )
        storage.add_turn(turn)

        ctx = await prepare_ask(
            convo_store=storage,
            memory_store=storage,
            emit_event=event_logger.append,
            conversation_id=convo.id,
            prompt_text="New question",
            interaction_router=RuleInteractionRouter(),
            router_policy=RouterPolicy(),
        )

        # Find positions
        time_idx = next(
            i for i, m in enumerate(ctx.messages) if m["role"] == "system" and "Last interaction:" in m["content"]
        )
        prior_turn_idx = next(i for i, m in enumerate(ctx.messages) if m["content"] == "Prior question")

        assert time_idx < prior_turn_idx

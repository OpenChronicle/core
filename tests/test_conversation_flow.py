from __future__ import annotations

from pathlib import Path

import pytest

from openchronicle.core.application.use_cases import ask_conversation, create_conversation, show_conversation
from openchronicle.core.infrastructure.llm.stub_adapter import StubLLMAdapter
from openchronicle.core.infrastructure.logging.event_logger import EventLogger
from openchronicle.core.infrastructure.persistence.sqlite_store import SqliteStore


@pytest.mark.asyncio
async def test_conversation_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OC_LLM_PROVIDER", "stub")
    monkeypatch.setenv("OC_LLM_FAST_POOL", "")
    monkeypatch.setenv("OC_LLM_QUALITY_POOL", "")

    db_path = tmp_path / "test.db"
    storage = SqliteStore(str(db_path))
    storage.init_schema()
    event_logger = EventLogger(storage)

    conversation = create_conversation.execute(
        storage=storage,
        convo_store=storage,
        emit_event=event_logger.append,
        title="Test Conversation",
    )

    stored_conversation = storage.get_conversation(conversation.id)
    assert stored_conversation is not None
    assert stored_conversation.id == conversation.id
    assert stored_conversation.title == "Test Conversation"

    llm = StubLLMAdapter()

    turn1 = await ask_conversation.execute(
        convo_store=storage,
        storage=storage,
        llm=llm,
        emit_event=event_logger.append,
        conversation_id=conversation.id,
        prompt_text="Hello",
        last_n=10,
    )

    turn2 = await ask_conversation.execute(
        convo_store=storage,
        storage=storage,
        llm=llm,
        emit_event=event_logger.append,
        conversation_id=conversation.id,
        prompt_text="How are you?",
        last_n=10,
    )

    assert turn1.turn_index == 1
    assert turn2.turn_index == 2

    assert turn1.provider == "stub"
    assert turn1.model == "stub-model"
    assert turn2.provider == "stub"
    assert turn2.model == "stub-model"

    _, turns = show_conversation.execute(convo_store=storage, conversation_id=conversation.id)
    assert [t.turn_index for t in turns] == [1, 2]
    assert turns[0].user_text == "Hello"
    assert turns[1].user_text == "How are you?"

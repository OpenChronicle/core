"""Interactive chat REPL for OpenChronicle conversations."""

from __future__ import annotations

import argparse
import asyncio

from openchronicle.core.application.runtime.container import CoreContainer
from openchronicle.core.application.use_cases import ask_conversation, create_conversation
from openchronicle.core.domain.ports.llm_port import LLMProviderError


async def _stream_turn(container: CoreContainer, conversation_id: str, prompt: str) -> str:
    """Stream a single turn, printing tokens as they arrive. Returns full text."""
    from openchronicle.core.application.routing.router_policy import RouterPolicy
    from openchronicle.core.application.services.llm_execution import stream_with_route
    from openchronicle.core.domain.models.conversation import Turn
    from openchronicle.core.domain.models.project import Event

    convo = container.storage.get_conversation(conversation_id)
    if convo is None:
        raise ValueError(f"Conversation not found: {conversation_id}")

    prior_turns = container.storage.list_turns(conversation_id, limit=10)

    messages: list[dict[str, str]] = [{"role": "system", "content": "You are a helpful assistant."}]
    for turn in prior_turns:
        messages.append({"role": "user", "content": turn.user_text})
        messages.append({"role": "assistant", "content": turn.assistant_text})
    messages.append({"role": "user", "content": prompt})

    router = RouterPolicy()
    route_decision = router.route(
        task_type="convo.ask",
        agent_role="user",
        agent_tags=None,
        desired_quality=None,
        provider_preference=None,
        current_task_tokens=None,
        max_tokens_per_task=None,
        rate_limit_triggered=False,
        rpm_limit=None,
    )

    container.event_logger.append(
        Event(
            project_id=convo.project_id,
            task_id=conversation_id,
            type="convo.turn_started",
            payload={"prompt_chars": len(prompt)},
        )
    )

    collected: list[str] = []
    async for chunk in stream_with_route(
        container.llm,
        route_decision,
        messages,
        max_output_tokens=512,
        temperature=0.2,
    ):
        if chunk.text:
            print(chunk.text, end="", flush=True)
            collected.append(chunk.text)
    print()  # newline after streaming

    assistant_text = "".join(collected)

    with container.storage.transaction():
        turn_index = container.storage.next_turn_index(conversation_id)
        turn = Turn(
            conversation_id=conversation_id,
            turn_index=turn_index,
            user_text=prompt,
            assistant_text=assistant_text,
            provider=route_decision.provider,
            model=route_decision.model,
            routing_reasons=route_decision.reasons,
        )
        container.storage.add_turn(turn)

    container.event_logger.append(
        Event(
            project_id=convo.project_id,
            task_id=conversation_id,
            type="convo.turn_completed",
            payload={
                "turn_id": turn.id,
                "turn_index": turn.turn_index,
                "provider": turn.provider,
                "model": turn.model,
            },
        )
    )

    return assistant_text


async def chat_loop(container: CoreContainer, conversation_id: str, *, stream: bool = True) -> int:
    """Interactive chat REPL."""
    print(f"Chat ({conversation_id[:8]}...) — type /quit to exit")
    while True:
        try:
            user_input = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        stripped = user_input.strip()
        if not stripped:
            continue
        if stripped in ("/quit", "/exit", "/q"):
            break

        try:
            if stream:
                print()
                await _stream_turn(container, conversation_id, stripped)
            else:
                turn = await ask_conversation.execute(
                    convo_store=container.storage,
                    storage=container.storage,
                    memory_store=container.storage,
                    llm=container.llm,
                    interaction_router=container.interaction_router,
                    emit_event=container.event_logger.append,
                    conversation_id=conversation_id,
                    prompt_text=stripped,
                    last_n=10,
                    top_k_memory=8,
                    include_pinned_memory=True,
                    allow_pii=False,
                    privacy_gate=getattr(container, "privacy_gate", None),
                    privacy_settings=getattr(container, "privacy_settings", None),
                )
                print(f"\n{turn.assistant_text}")
        except (ValueError, LLMProviderError) as exc:
            print(f"\nError: {exc}")
            continue

    return 0


def _resolve_conversation(args: argparse.Namespace, container: CoreContainer) -> str | None:
    """Resolve conversation ID from args, returning None on error."""
    if args.conversation_id:
        return str(args.conversation_id)

    if args.resume:
        convos = container.storage.list_conversations(limit=1)
        if not convos:
            print("No conversations to resume. Start a new one with: oc chat")
            return None
        print(f"Resuming: {convos[0].title or '(untitled)'} ({convos[0].id[:8]}...)")
        return convos[0].id

    conversation = create_conversation.execute(
        storage=container.storage,
        convo_store=container.storage,
        emit_event=container.event_logger.append,
        title=args.title or "Chat session",
    )
    return conversation.id


def cmd_chat(args: argparse.Namespace, container: CoreContainer) -> int:
    """oc chat [--conversation-id ID] [--resume] [--title TITLE] [--no-stream]"""
    convo_id = _resolve_conversation(args, container)
    if convo_id is None:
        return 1
    stream = not getattr(args, "no_stream", False)
    return asyncio.run(chat_loop(container, convo_id, stream=stream))

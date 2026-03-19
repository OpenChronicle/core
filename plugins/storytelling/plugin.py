from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from openchronicle.core.application.runtime.task_registry import TaskHandlerRegistry
from openchronicle.core.domain.models.project import Event, Task
from openchronicle.core.domain.ports.plugin_port import PluginRegistry

from .application.bookmark_manager import create_bookmark, list_bookmarks
from .application.branching import generate_branches
from .application.consistency_checker import check_consistency
from .application.conversation_mode import story_prompt_builder
from .application.dice_engine import roll_notation
from .application.emotional_analyzer import analyze_emotional_arc
from .application.persona_extractor import (
    MULTIMODAL_REQUIRED_MESSAGE,
    extract_persona,
)
from .application.resolution import resolve_action
from .application.scene_handler import generate_scene
from .application.stat_manager import (
    get_stat_modifier_for_resolution,
    load_stat_block,
    update_stat,
)
from .application.timeline_assembler import assemble_timeline
from .domain.mechanics import DifficultyLevel, OutcomeType, ResolutionType
from .domain.modes import EngagementMode
from .domain.persona import PersonaExtractionStatus, PersonaSource
from .domain.stats import StatType
from .domain.timeline import BookmarkType
from .helpers import format_draft, hash_text
from .importer import import_project

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Handler: story.draft (demo)
# ---------------------------------------------------------------------------


async def _story_draft_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, str]:
    await asyncio.sleep(0)
    context = context or {}
    emit_event = context.get("emit_event")
    agent_id = context.get("agent_id")

    prompt = task.payload.get("prompt") or "Tell a short story."
    if emit_event:
        emit_event(
            Event(
                project_id=task.project_id,
                task_id=task.id,
                agent_id=agent_id,
                type="plugin.received_task",
                payload={"text_hash": hash_text(prompt)},
            )
        )

    draft = format_draft(prompt)

    if emit_event:
        emit_event(
            Event(
                project_id=task.project_id,
                task_id=task.id,
                agent_id=agent_id,
                type="plugin.completed_task",
                payload={"draft_preview": draft[:80]},
            )
        )

    return {"draft": draft}


# ---------------------------------------------------------------------------
# Handler: story.import
# ---------------------------------------------------------------------------


async def _story_import_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Import a storytelling project from a directory of text files."""
    await asyncio.sleep(0)
    ctx = context or {}
    memory_save = ctx.get("memory_save")
    emit_event = ctx.get("emit_event")
    agent_id = ctx.get("agent_id")

    payload = task.payload if isinstance(task.payload, dict) else {}
    source_dir: str = payload.get("source_dir", "")
    project_name: str = payload.get("project_name", "Unnamed Project")
    dry_run: bool = payload.get("dry_run", False)

    if not source_dir:
        raise ValueError("source_dir is required in task payload")
    if memory_save is None:
        raise RuntimeError("memory_save not available in handler context")

    if emit_event:
        emit_event(
            Event(
                project_id=task.project_id,
                task_id=task.id,
                agent_id=agent_id,
                type="plugin.received_task",
                payload={"source_dir": source_dir, "project_name": project_name},
            )
        )

    result = import_project(
        source_dir=source_dir,
        project_name=project_name,
        memory_save=memory_save,
        dry_run=dry_run,
    )

    if emit_event:
        emit_event(
            Event(
                project_id=task.project_id,
                task_id=task.id,
                agent_id=agent_id,
                type="plugin.completed_task",
                payload={
                    "project_name": result.project_name,
                    "imported": result.imported,
                    "skipped": result.skipped,
                },
            )
        )

    return {
        "project_name": result.project_name,
        "imported": result.imported,
        "assets_uploaded": result.assets_uploaded,
        "skipped": result.skipped,
        "warnings": result.warnings,
    }


# ---------------------------------------------------------------------------
# Handler: story.scene
# ---------------------------------------------------------------------------


async def _story_scene_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate a storytelling scene using assembled context and LLM."""
    ctx = context or {}
    memory_search = ctx.get("memory_search")
    memory_save = ctx.get("memory_save")
    llm_complete = ctx.get("llm_complete")
    emit_event = ctx.get("emit_event")
    agent_id = ctx.get("agent_id")

    if memory_search is None:
        raise RuntimeError("memory_search not available in handler context")
    if memory_save is None:
        raise RuntimeError("memory_save not available in handler context")
    if llm_complete is None:
        raise RuntimeError("llm_complete not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    user_prompt: str = payload.get("prompt", "")
    mode_str: str = payload.get("mode", "director")
    canon: bool = payload.get("canon", True)
    player_character: str | None = payload.get("player_character")
    location: str | None = payload.get("location")
    save_scene: bool = payload.get("save_scene", False)
    max_output_tokens: int = payload.get("max_output_tokens", 2048)
    temperature: float = payload.get("temperature", 0.8)
    validate_consistency: bool = payload.get("validate_consistency", False)
    analyze_emotion: bool = payload.get("analyze_emotion", False)

    if not user_prompt:
        raise ValueError("prompt is required in task payload")

    # Resolve engagement mode
    try:
        mode = EngagementMode(mode_str.lower())
    except ValueError:
        valid = ", ".join(m.value for m in EngagementMode)
        raise ValueError(f"Invalid mode '{mode_str}'. Valid modes: {valid}") from None

    if emit_event:
        emit_event(
            Event(
                project_id=task.project_id,
                task_id=task.id,
                agent_id=agent_id,
                type="plugin.received_task",
                payload={
                    "handler": "story.scene",
                    "mode": mode.value,
                    "canon": canon,
                    "prompt_len": len(user_prompt),
                },
            )
        )

    result = await generate_scene(
        memory_search=memory_search,
        memory_save=memory_save,
        llm_complete=llm_complete,
        user_prompt=user_prompt,
        mode=mode,
        canon=canon,
        player_character=player_character,
        location=location,
        save_scene=save_scene,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        validate_consistency=validate_consistency,
        analyze_emotion=analyze_emotion,
    )

    if emit_event:
        emit_event(
            Event(
                project_id=task.project_id,
                task_id=task.id,
                agent_id=agent_id,
                type="plugin.completed_task",
                payload={
                    "handler": "story.scene",
                    "mode": result.mode,
                    "canon": result.canon,
                    "scene_len": len(result.scene_text),
                    "characters_used": result.characters_used,
                    "scene_id": result.scene_id,
                },
            )
        )

    return {
        "scene_text": result.scene_text,
        "mode": result.mode,
        "canon": result.canon,
        "player_character": result.player_character,
        "location": result.location,
        "characters_used": result.characters_used,
        "scene_id": result.scene_id,
    }


# ---------------------------------------------------------------------------
# Handler: story.bookmark.create
# ---------------------------------------------------------------------------


async def _story_bookmark_create_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a bookmark."""
    await asyncio.sleep(0)
    ctx = context or {}
    memory_save = ctx.get("memory_save")
    if memory_save is None:
        raise RuntimeError("memory_save not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    label: str = payload.get("label", "")
    if not label:
        raise ValueError("label is required")

    type_str: str = payload.get("bookmark_type", "user")
    scene_id: str | None = payload.get("scene_id")
    chapter: str | None = payload.get("chapter")
    position: int = payload.get("position", 0)

    try:
        bm_type = BookmarkType(type_str.lower())
    except ValueError:
        valid = ", ".join(b.value for b in BookmarkType)
        raise ValueError(f"Invalid bookmark type '{type_str}'. Valid: {valid}") from None

    bm = create_bookmark(memory_save, label, bm_type, scene_id, chapter, position)

    return {
        "id": bm.id,
        "label": bm.label,
        "bookmark_type": bm.bookmark_type.value,
        "scene_id": bm.scene_id,
        "chapter": bm.chapter,
    }


# ---------------------------------------------------------------------------
# Handler: story.bookmark.list
# ---------------------------------------------------------------------------


async def _story_bookmark_list_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """List bookmarks, optionally filtered by type."""
    await asyncio.sleep(0)
    ctx = context or {}
    memory_search = ctx.get("memory_search")
    if memory_search is None:
        raise RuntimeError("memory_search not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    type_str: str | None = payload.get("bookmark_type")

    bm_type = None
    if type_str:
        with contextlib.suppress(ValueError):
            bm_type = BookmarkType(type_str.lower())

    bookmarks = list_bookmarks(memory_search, bm_type)

    return {
        "count": len(bookmarks),
        "bookmarks": [
            {
                "id": bm.id,
                "label": bm.label,
                "bookmark_type": bm.bookmark_type.value,
                "scene_id": bm.scene_id,
                "chapter": bm.chapter,
                "position": bm.position,
            }
            for bm in bookmarks
        ],
    }


# ---------------------------------------------------------------------------
# Handler: story.timeline
# ---------------------------------------------------------------------------


async def _story_timeline_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assemble a chronological timeline."""
    await asyncio.sleep(0)
    ctx = context or {}
    memory_search = ctx.get("memory_search")
    if memory_search is None:
        raise RuntimeError("memory_search not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    chapter_filter: str | None = payload.get("chapter")

    timeline = assemble_timeline(memory_search, chapter_filter)

    return {
        "total_entries": len(timeline.entries),
        "chapters": list(timeline.chapters.keys()),
        "entries": [
            {
                "memory_id": e.memory_id,
                "entry_type": e.entry_type,
                "label": e.label,
                "chapter": e.chapter,
                "created_at": e.created_at,
            }
            for e in timeline.entries
        ],
    }


# ---------------------------------------------------------------------------
# Handler: story.consistency.check
# ---------------------------------------------------------------------------


async def _story_consistency_check_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run LLM-based consistency check on content."""
    ctx = context or {}
    memory_search = ctx.get("memory_search")
    llm_complete = ctx.get("llm_complete")
    if memory_search is None:
        raise RuntimeError("memory_search not available in handler context")
    if llm_complete is None:
        raise RuntimeError("llm_complete not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    content: str = payload.get("content", "")
    content_type: str = payload.get("content_type", "scene")

    if not content:
        raise ValueError("content is required")

    report = await check_consistency(memory_search, llm_complete, content, content_type)

    return {
        "passed": report.passed,
        "checked_items": report.checked_items,
        "summary": report.summary,
        "issues": [
            {
                "severity": i.severity,
                "description": i.description,
                "entity_type": i.entity_type,
                "entity_name": i.entity_name,
            }
            for i in report.issues
        ],
    }


# ---------------------------------------------------------------------------
# Handler: story.emotion.analyze
# ---------------------------------------------------------------------------


async def _story_emotion_analyze_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run LLM-based emotional arc analysis."""
    ctx = context or {}
    memory_search = ctx.get("memory_search")
    llm_complete = ctx.get("llm_complete")
    if memory_search is None:
        raise RuntimeError("memory_search not available in handler context")
    if llm_complete is None:
        raise RuntimeError("llm_complete not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    scene_text: str = payload.get("scene_text", "")
    character_names: list[str] | None = payload.get("character_names")

    if not scene_text:
        raise ValueError("scene_text is required")

    report = await analyze_emotional_arc(memory_search, llm_complete, scene_text, character_names)

    return {
        "arc_summary": report.arc_summary,
        "beats": [
            {
                "character_name": b.character_name,
                "emotion": b.emotion.value,
                "intensity": b.intensity,
                "trigger": b.trigger,
                "scene_position": b.scene_position,
            }
            for b in report.beats
        ],
        "loops": [
            {
                "character_name": loop.character_name,
                "emotion": loop.emotion.value,
                "occurrence_count": loop.occurrence_count,
                "confidence": loop.confidence,
            }
            for loop in report.loops
        ],
        "character_arcs": {name: [b.emotion.value for b in beats] for name, beats in report.character_arcs.items()},
    }


# ---------------------------------------------------------------------------
# Handler: story.roll
# ---------------------------------------------------------------------------


async def _story_roll_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Roll dice using standard notation."""
    await asyncio.sleep(0)
    payload = task.payload if isinstance(task.payload, dict) else {}
    notation: str = payload.get("notation", "d20")
    advantage: bool = payload.get("advantage", False)
    disadvantage: bool = payload.get("disadvantage", False)

    result = roll_notation(notation, advantage=advantage, disadvantage=disadvantage)

    return {
        "dice_type": result.dice_type.value,
        "rolls": list(result.rolls),
        "modifier": result.modifier,
        "total": result.total,
        "advantage": result.advantage,
        "disadvantage": result.disadvantage,
    }


# ---------------------------------------------------------------------------
# Handler: story.resolve
# ---------------------------------------------------------------------------


async def _story_resolve_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Roll + difficulty check + optional stat modifier."""
    await asyncio.sleep(0)
    ctx = context or {}
    memory_search = ctx.get("memory_search")

    payload = task.payload if isinstance(task.payload, dict) else {}

    resolution_str: str = payload.get("resolution_type", "skill_check")
    difficulty_str: str = payload.get("difficulty", "moderate")
    character_name: str | None = payload.get("character_name")
    advantage: bool = payload.get("advantage", False)
    disadvantage: bool = payload.get("disadvantage", False)

    try:
        resolution_type = ResolutionType(resolution_str.lower())
    except ValueError:
        valid = ", ".join(r.value for r in ResolutionType)
        raise ValueError(f"Invalid resolution type '{resolution_str}'. Valid: {valid}") from None

    try:
        difficulty = DifficultyLevel[difficulty_str.upper()]
    except KeyError:
        valid = ", ".join(d.name.lower() for d in DifficultyLevel)
        raise ValueError(f"Invalid difficulty '{difficulty_str}'. Valid: {valid}") from None

    # Get stat modifier if character provided
    char_modifier = 0
    if character_name and memory_search:
        stat_block = load_stat_block(memory_search, character_name)
        if stat_block:
            char_modifier = get_stat_modifier_for_resolution(stat_block, resolution_type)

    result = resolve_action(
        resolution_type,
        difficulty,
        char_modifier,
        advantage=advantage,
        disadvantage=disadvantage,
    )

    return {
        "resolution_type": result.resolution_type.value,
        "outcome": result.outcome.value,
        "dice_type": result.dice_roll.dice_type.value,
        "rolls": list(result.dice_roll.rolls),
        "modifier": result.dice_roll.modifier,
        "total": result.dice_roll.total,
        "difficulty_check": result.difficulty_check,
        "success_margin": result.success_margin,
        "character_name": character_name,
        "character_modifier": char_modifier,
    }


# ---------------------------------------------------------------------------
# Handler: story.stats.get
# ---------------------------------------------------------------------------


async def _story_stats_get_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load a character's stat block from memory."""
    await asyncio.sleep(0)
    ctx = context or {}
    memory_search = ctx.get("memory_search")
    if memory_search is None:
        raise RuntimeError("memory_search not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    character_name: str = payload.get("character_name", "")
    if not character_name:
        raise ValueError("character_name is required")

    stat_block = load_stat_block(memory_search, character_name)
    if stat_block is None:
        return {"found": False, "character_name": character_name, "values": {}}

    return {"found": True, "character_name": character_name, "values": stat_block.values}


# ---------------------------------------------------------------------------
# Handler: story.stats.set
# ---------------------------------------------------------------------------


async def _story_stats_set_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Save or update a character stat."""
    await asyncio.sleep(0)
    ctx = context or {}
    memory_search = ctx.get("memory_search")
    memory_save = ctx.get("memory_save")
    memory_update = ctx.get("memory_update")
    if memory_search is None or memory_save is None:
        raise RuntimeError("memory_search and memory_save required in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    character_name: str = payload.get("character_name", "")
    stat_str: str = payload.get("stat", "")
    value: int = payload.get("value", 10)
    reason: str = payload.get("reason", "Manual update")

    if not character_name:
        raise ValueError("character_name is required")
    if not stat_str:
        raise ValueError("stat is required")

    try:
        stat_type = StatType(stat_str.lower())
    except ValueError:
        valid = ", ".join(s.value for s in StatType)
        raise ValueError(f"Invalid stat '{stat_str}'. Valid: {valid}") from None

    updated = update_stat(memory_search, memory_save, memory_update, character_name, stat_type, value, reason)

    return {
        "character_name": character_name,
        "stat": stat_type.value,
        "value": updated.values.get(stat_type.value, value),
        "values": updated.values,
    }


# ---------------------------------------------------------------------------
# Handler: story.branch
# ---------------------------------------------------------------------------


async def _story_branch_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate narrative branches from a resolution result."""
    ctx = context or {}
    llm_complete = ctx.get("llm_complete")
    if llm_complete is None:
        raise RuntimeError("llm_complete not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}

    # Reconstruct a minimal resolution result for branching
    resolution_str: str = payload.get("resolution_type", "skill_check")
    outcome_str: str = payload.get("outcome", "success")
    margin: int = payload.get("success_margin", 0)
    character_name: str | None = payload.get("character_name")
    context_summary: str = payload.get("context_summary", "")
    branch_count: int = payload.get("branch_count", 3)

    resolution_type = ResolutionType(resolution_str.lower())
    outcome = OutcomeType(outcome_str.lower())

    # Build a minimal resolution result for the branching engine
    minimal_result = type(
        "MinimalResult",
        (),
        {
            "resolution_type": resolution_type,
            "outcome": outcome,
            "success_margin": margin,
            "character_name": character_name,
        },
    )()

    branch_options = await generate_branches(
        llm_complete,
        minimal_result,
        context_summary,
        branch_count=branch_count,
    )

    return {
        "outcome": outcome.value,
        "branches": [
            {
                "description": b.description,
                "consequence_type": b.consequence_type,
                "transition_hint": b.transition_hint,
            }
            for b in branch_options.branches
        ],
    }


# ---------------------------------------------------------------------------
# Handler: story.persona.extract
# ---------------------------------------------------------------------------


async def _story_persona_extract_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract a persona from text sources."""
    ctx = context or {}
    memory_search = ctx.get("memory_search")
    memory_save = ctx.get("memory_save")
    llm_complete = ctx.get("llm_complete")
    if memory_search is None or memory_save is None:
        raise RuntimeError("memory_search and memory_save required in handler context")
    if llm_complete is None:
        raise RuntimeError("llm_complete not available in handler context")

    payload = task.payload if isinstance(task.payload, dict) else {}
    character_name: str = payload.get("character_name", "")
    source_text: str = payload.get("source_text", "")

    if not character_name:
        raise ValueError("character_name is required")
    if not source_text:
        raise ValueError("source_text is required")

    sources = [PersonaSource(source_type="text", content_ref=source_text)]
    return await extract_persona(memory_search, memory_save, llm_complete, character_name, sources)


# ---------------------------------------------------------------------------
# Handler: story.persona.status
# ---------------------------------------------------------------------------


async def _story_persona_status_handler(task: Task, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Report persona extraction capability status."""
    await asyncio.sleep(0)
    return {
        "text_extraction": PersonaExtractionStatus.READY.value,
        "image_extraction": PersonaExtractionStatus.NOT_AVAILABLE.value,
        "voice_extraction": PersonaExtractionStatus.NOT_AVAILABLE.value,
        "video_extraction": PersonaExtractionStatus.NOT_AVAILABLE.value,
        "message": MULTIMODAL_REQUIRED_MESSAGE,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(
    registry: PluginRegistry, handler_registry: TaskHandlerRegistry, context: dict[str, Any] | None = None
) -> None:
    handler_registry.register("story.draft", _story_draft_handler)
    handler_registry.register("story.import", _story_import_handler)
    handler_registry.register("story.scene", _story_scene_handler)
    handler_registry.register("story.persona.extract", _story_persona_extract_handler)
    handler_registry.register("story.persona.status", _story_persona_status_handler)
    handler_registry.register("story.consistency.check", _story_consistency_check_handler)
    handler_registry.register("story.emotion.analyze", _story_emotion_analyze_handler)
    handler_registry.register("story.bookmark.create", _story_bookmark_create_handler)
    handler_registry.register("story.bookmark.list", _story_bookmark_list_handler)
    handler_registry.register("story.timeline", _story_timeline_handler)
    handler_registry.register("story.roll", _story_roll_handler)
    handler_registry.register("story.resolve", _story_resolve_handler)
    handler_registry.register("story.stats.get", _story_stats_get_handler)
    handler_registry.register("story.stats.set", _story_stats_set_handler)
    handler_registry.register("story.branch", _story_branch_handler)
    registry.register_agent_template(
        {"role": "storyteller", "description": "Imports and manages narrative content, generates scenes."}
    )

    registry.register_mode_prompt_builder("story", story_prompt_builder)

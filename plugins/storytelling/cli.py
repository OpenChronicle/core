"""Storytelling plugin CLI commands (plugin protocol).

Discovered dynamically by ``_discover_plugin_cli_commands()`` in the core CLI.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from openchronicle.core.infrastructure.wiring.container import CoreContainer

# ---------------------------------------------------------------------------
# Plugin CLI protocol
# ---------------------------------------------------------------------------

COMMAND = "story"
HELP = "Storytelling project commands"


def setup_parser(sub: argparse._SubParsersAction) -> None:
    """Register ``oc story`` subcommands on the root subparser."""
    story_cmd = sub.add_parser(COMMAND, help=HELP)
    story_sub = story_cmd.add_subparsers(dest="story_command")

    # oc story import <path> --project-id <id> [--project-name <name>] [--dry-run]
    import_parser = story_sub.add_parser("import", help="Import a storytelling project from a directory")
    import_parser.add_argument("path", help="Path to the project directory")
    import_parser.add_argument("--project-id", required=True, help="OC project ID")
    import_parser.add_argument("--project-name", help="Project name (default: directory name)")
    import_parser.add_argument("--dry-run", action="store_true", help="Parse and classify without saving")

    # oc story list --project-id <id> [--type <type>]
    list_parser = story_sub.add_parser("list", help="List imported storytelling content")
    list_parser.add_argument("--project-id", required=True, help="OC project ID")
    list_parser.add_argument(
        "--type",
        choices=["character", "location", "style-guide", "scene", "instructions", "worldbuilding", "all"],
        default="all",
        help="Filter by content type",
    )

    # oc story show <memory-id>
    show_parser = story_sub.add_parser("show", help="Show a single storytelling memory item")
    show_parser.add_argument("memory_id", help="Memory item ID")

    # oc story scene --project-id <id> [--mode <mode>] [--sandbox] [--character <name>] [--location <name>] [--save] <prompt...>
    scene_parser = story_sub.add_parser("scene", help="Generate a storytelling scene")
    scene_parser.add_argument("prompt", nargs="+", help="Scene prompt / direction")
    scene_parser.add_argument("--project-id", required=True, help="OC project ID")
    scene_parser.add_argument(
        "--mode",
        choices=["participant", "director", "audience"],
        default="director",
        help="Engagement mode (default: director)",
    )
    canon_group = scene_parser.add_mutually_exclusive_group()
    canon_group.add_argument("--canon", action="store_true", default=True, help="Canon mode (default)")
    canon_group.add_argument("--sandbox", action="store_true", help="Sandbox (non-canon) mode")
    scene_parser.add_argument("--character", help="Player character name (for participant mode)")
    scene_parser.add_argument("--location", help="Location hint for context retrieval")
    scene_parser.add_argument("--save", action="store_true", help="Save the generated scene as a memory item")
    scene_parser.add_argument("--max-tokens", type=int, default=2048, help="Max output tokens (default: 2048)")
    scene_parser.add_argument("--temperature", type=float, default=0.8, help="LLM temperature (default: 0.8)")
    scene_parser.add_argument("--check-consistency", action="store_true", help="Run consistency check on output")
    scene_parser.add_argument("--analyze-emotion", action="store_true", help="Run emotional arc analysis on output")

    # oc story characters --project-id <id> [--primary-only]
    chars_parser = story_sub.add_parser("characters", help="List imported characters")
    chars_parser.add_argument("--project-id", required=True, help="OC project ID")
    chars_parser.add_argument("--primary-only", action="store_true", help="Show only primary characters")

    # oc story locations --project-id <id>
    locs_parser = story_sub.add_parser("locations", help="List imported locations")
    locs_parser.add_argument("--project-id", required=True, help="OC project ID")

    # oc story search --project-id <id> <query>
    search_parser = story_sub.add_parser("search", help="Search storytelling content")
    search_parser.add_argument("query", nargs="+", help="Search query")
    search_parser.add_argument("--project-id", required=True, help="OC project ID")

    # oc story persona extract <name> --project-id <id> --source-text <text>
    persona_parser = story_sub.add_parser("persona", help="Persona extraction")
    persona_sub = persona_parser.add_subparsers(dest="persona_command")

    persona_extract_parser = persona_sub.add_parser("extract", help="Extract persona from text")
    persona_extract_parser.add_argument("name", help="Character name")
    persona_extract_parser.add_argument("--project-id", required=True, help="OC project ID")
    persona_extract_parser.add_argument("--source-text", required=True, help="Text describing the character")

    persona_sub.add_parser("status", help="Show persona extraction capabilities")

    # oc story consistency <text-or-memory-id> --project-id <id>
    consist_parser = story_sub.add_parser("consistency", help="Check content for consistency")
    consist_parser.add_argument("content", nargs="+", help="Text content to check (or memory ID)")
    consist_parser.add_argument("--project-id", required=True, help="OC project ID")

    # oc story emotion <text-or-memory-id> --project-id <id> [--characters <names>]
    emotion_parser = story_sub.add_parser("emotion", help="Analyze emotional arc")
    emotion_parser.add_argument("content", nargs="+", help="Scene text to analyze (or memory ID)")
    emotion_parser.add_argument("--project-id", required=True, help="OC project ID")
    emotion_parser.add_argument("--characters", help="Comma-separated character names to focus on")

    # oc story bookmark create <label> --project-id <id> [--type <type>] [--scene-id <id>] [--chapter <name>]
    bm_parser = story_sub.add_parser("bookmark", help="Bookmark management")
    bm_sub = bm_parser.add_subparsers(dest="bookmark_command")

    bm_create_parser = bm_sub.add_parser("create", help="Create a bookmark")
    bm_create_parser.add_argument("label", help="Bookmark label")
    bm_create_parser.add_argument("--project-id", required=True, help="OC project ID")
    bm_create_parser.add_argument(
        "--type", choices=["user", "milestone", "chapter"], default="user", help="Bookmark type"
    )
    bm_create_parser.add_argument("--scene-id", help="Scene memory ID to link")
    bm_create_parser.add_argument("--chapter", help="Chapter name")

    bm_list_parser = bm_sub.add_parser("list", help="List bookmarks")
    bm_list_parser.add_argument("--project-id", required=True, help="OC project ID")
    bm_list_parser.add_argument("--type", choices=["user", "auto", "milestone", "chapter"], help="Filter by type")

    # oc story timeline --project-id <id> [--chapter <name>]
    timeline_parser = story_sub.add_parser("timeline", help="Show story timeline")
    timeline_parser.add_argument("--project-id", required=True, help="OC project ID")
    timeline_parser.add_argument("--chapter", help="Filter by chapter name")

    # oc story roll <notation> [--advantage] [--disadvantage]
    roll_parser = story_sub.add_parser("roll", help="Roll dice using standard notation")
    roll_parser.add_argument("notation", help="Dice notation (e.g. d20, 3d6+2, fudge, coin)")
    roll_parser.add_argument("--advantage", action="store_true", help="Roll with advantage (D20 only)")
    roll_parser.add_argument("--disadvantage", action="store_true", help="Roll with disadvantage (D20 only)")

    # oc story resolve <type> --difficulty <level> [--character <name>] [--project-id <id>]
    resolve_parser = story_sub.add_parser("resolve", help="Roll + difficulty check + stat modifier")
    resolve_parser.add_argument("resolution_type", help="Resolution type (e.g. skill_check, combat_action)")
    resolve_parser.add_argument(
        "--difficulty", required=True, help="Difficulty level (trivial, easy, moderate, hard, very_hard, legendary)"
    )
    resolve_parser.add_argument("--character", help="Character name for stat modifier lookup")
    resolve_parser.add_argument("--project-id", help="OC project ID (required if --character is used)")
    resolve_parser.add_argument("--advantage", action="store_true", help="Roll with advantage")
    resolve_parser.add_argument("--disadvantage", action="store_true", help="Roll with disadvantage")

    # oc story stats <character> --project-id <id>
    stats_parser = story_sub.add_parser("stats", help="Show character stat block")
    stats_parser.add_argument("character", help="Character name")
    stats_parser.add_argument("--project-id", required=True, help="OC project ID")

    # oc story stats-set <character> <stat> <value> --project-id <id> [--reason <text>]
    stats_set_parser = story_sub.add_parser("stats-set", help="Set a character stat")
    stats_set_parser.add_argument("character", help="Character name")
    stats_set_parser.add_argument("stat", help="Stat name (e.g. strength, intelligence)")
    stats_set_parser.add_argument("value", type=int, help="Stat value (1-20)")
    stats_set_parser.add_argument("--project-id", required=True, help="OC project ID")
    stats_set_parser.add_argument("--reason", default="Manual update", help="Reason for the change")


def run(args: argparse.Namespace, container: CoreContainer) -> int:
    """Dispatch ``oc story <subcommand>``."""
    story_dispatch: dict[str, Callable[[argparse.Namespace, CoreContainer], int]] = {
        "import": _cmd_story_import,
        "list": _cmd_story_list,
        "show": _cmd_story_show,
        "scene": _cmd_story_scene,
        "characters": _cmd_story_characters,
        "locations": _cmd_story_locations,
        "search": _cmd_story_search,
        "persona": _cmd_story_persona,
        "consistency": _cmd_story_consistency,
        "emotion": _cmd_story_emotion,
        "bookmark": _cmd_story_bookmark,
        "timeline": _cmd_story_timeline,
        "roll": _cmd_story_roll,
        "resolve": _cmd_story_resolve,
        "stats": _cmd_story_stats,
        "stats-set": _cmd_story_stats_set,
    }
    handler = story_dispatch.get(args.story_command)
    if handler is None:
        print(
            "Usage: oc story <import|list|show|scene|characters|locations|search"
            "|persona|consistency|emotion|bookmark|timeline|roll|resolve|stats|stats-set>"
        )
        return 1
    return handler(args, container)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _cmd_story_import(args: argparse.Namespace, container: CoreContainer) -> int:
    """Import a storytelling project via the orchestrator."""
    from pathlib import Path

    from openchronicle.core.application.use_cases import run_task

    project_id = args.project_id
    source_path = Path(args.path)
    project_name = args.project_name or source_path.name
    dry_run = args.dry_run

    # Validate project exists
    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found.")
        print("List projects with: oc project list")
        return 1

    if not source_path.is_dir():
        print(f"Error: Directory not found: {args.path}")
        return 1

    action = "Dry-run import" if dry_run else "Importing"
    print(f"{action} '{project_name}' from {source_path}...")

    # Submit and execute through the orchestrator
    task = run_task.submit(
        container.orchestrator,
        project_id,
        "plugin.invoke",
        {
            "handler": "story.import",
            "input": {
                "source_dir": str(source_path),
                "project_name": project_name,
                "dry_run": dry_run,
            },
        },
    )

    try:
        result = asyncio.run(run_task.execute(container.orchestrator, task.id))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: Import failed: {exc}")
        return 1

    # Display results
    result_data = result.result if hasattr(result, "result") else result
    if isinstance(result_data, str):
        result_data = json.loads(result_data)

    if isinstance(result_data, dict):
        imported = result_data.get("imported", {})
        skipped = result_data.get("skipped", [])
        warnings = result_data.get("warnings", [])

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Import complete: {project_name}")
        print("-" * 40)
        total = 0
        for content_type, count in sorted(imported.items()):
            print(f"  {content_type:20s}  {count}")
            total += count
        print(f"  {'total':20s}  {total}")

        if skipped:
            print(f"\nSkipped ({len(skipped)}):")
            for name in skipped:
                print(f"  - {name}")

        if warnings:
            print(f"\nWarnings ({len(warnings)}):")
            for warning in warnings:
                print(f"  ! {warning}")
    else:
        print(f"Import result: {result_data}")

    return 0


def _cmd_story_list(args: argparse.Namespace, container: CoreContainer) -> int:
    """List imported storytelling content from memory."""
    from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort

    project_id = args.project_id
    content_type = args.type

    memory_store: MemoryStorePort = container.storage

    # Search with tag filtering
    tags = ["story"]
    if content_type != "all":
        tags.append(content_type)

    items = memory_store.search_memory("story", project_id=project_id, top_k=200, tags=tags)

    if not items:
        print("No storytelling content found.")
        return 0

    print(f"Storytelling content ({len(items)} items):")
    print(f"{'ID':38s}  {'Type':15s}  {'Preview'}")
    print("-" * 80)
    for item in items:
        # Extract content type from tags
        item_type = _extract_type_from_tags(item.tags)
        # First line of content as preview
        preview = item.content.split("\n")[0][:50] if item.content else ""
        print(f"{item.id:38s}  {item_type:15s}  {preview}")

    return 0


def _cmd_story_show(args: argparse.Namespace, container: CoreContainer) -> int:
    """Show a single storytelling memory item."""
    from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort

    memory_store: MemoryStorePort = container.storage
    item = memory_store.get_memory(args.memory_id)

    if item is None:
        print(f"Error: Memory item '{args.memory_id}' not found.")
        return 1

    print(f"ID:      {item.id}")
    print(f"Tags:    {', '.join(item.tags)}")
    print(f"Pinned:  {item.pinned}")
    print(f"Created: {item.created_at}")
    print("-" * 40)
    print(item.content)

    return 0


def _cmd_story_scene(args: argparse.Namespace, container: CoreContainer) -> int:
    """Generate a storytelling scene via the orchestrator."""
    from openchronicle.core.application.use_cases import run_task

    project_id = args.project_id
    user_prompt = " ".join(args.prompt)
    mode = args.mode
    canon = not args.sandbox
    character = args.character
    location = args.location
    save_scene = args.save
    max_tokens = args.max_tokens
    temperature = args.temperature

    # Validate project exists
    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found.")
        print("List projects with: oc project list")
        return 1

    canon_label = "canon" if canon else "sandbox"
    print(f"Generating scene ({mode}, {canon_label})...")

    task = run_task.submit(
        container.orchestrator,
        project_id,
        "plugin.invoke",
        {
            "handler": "story.scene",
            "input": {
                "prompt": user_prompt,
                "mode": mode,
                "canon": canon,
                "player_character": character,
                "location": location,
                "save_scene": save_scene,
                "max_output_tokens": max_tokens,
                "temperature": temperature,
                "validate_consistency": getattr(args, "check_consistency", False),
                "analyze_emotion": getattr(args, "analyze_emotion", False),
            },
        },
    )

    try:
        result = asyncio.run(run_task.execute(container.orchestrator, task.id))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: Scene generation failed: {exc}")
        return 1

    result_data = result.result if hasattr(result, "result") else result
    if isinstance(result_data, str):
        result_data = json.loads(result_data)

    if isinstance(result_data, dict):
        scene_text = result_data.get("scene_text", "")
        scene_mode = result_data.get("mode", mode)
        scene_canon = result_data.get("canon", canon)
        chars_used = result_data.get("characters_used", 0)
        scene_id = result_data.get("scene_id")

        print(f"\n{'=' * 60}")
        print(f"Mode: {scene_mode} | Canon: {scene_canon} | Characters: {chars_used}")
        if scene_id:
            print(f"Saved as: {scene_id}")
        print(f"{'=' * 60}\n")
        print(scene_text)
    else:
        print(f"Scene result: {result_data}")

    return 0


def _extract_type_from_tags(tags: list[str]) -> str:
    """Extract the content type from story tags."""
    type_tags = {"character", "location", "style-guide", "instructions", "scene", "worldbuilding", "project-meta"}
    for tag in tags:
        if tag in type_tags:
            return tag
    return "unknown"


def _cmd_story_characters(args: argparse.Namespace, container: CoreContainer) -> int:
    """List imported characters from storytelling memory."""
    from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort

    memory_store: MemoryStorePort = container.storage
    tags = ["story", "character"]
    if args.primary_only:
        tags.append("primary")

    items = memory_store.search_memory("character", project_id=args.project_id, top_k=200, tags=tags)
    if not items:
        print("No characters found.")
        return 0

    print(f"Characters ({len(items)}):")
    print(f"{'ID':38s}  {'Preview'}")
    print("-" * 80)
    for item in items:
        preview = item.content.split("\n")[0][:60] if item.content else ""
        print(f"{item.id:38s}  {preview}")
    return 0


def _cmd_story_locations(args: argparse.Namespace, container: CoreContainer) -> int:
    """List imported locations from storytelling memory."""
    from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort

    memory_store: MemoryStorePort = container.storage
    items = memory_store.search_memory("location", project_id=args.project_id, top_k=200, tags=["story", "location"])
    if not items:
        print("No locations found.")
        return 0

    print(f"Locations ({len(items)}):")
    print(f"{'ID':38s}  {'Preview'}")
    print("-" * 80)
    for item in items:
        preview = item.content.split("\n")[0][:60] if item.content else ""
        print(f"{item.id:38s}  {preview}")
    return 0


def _cmd_story_search(args: argparse.Namespace, container: CoreContainer) -> int:
    """Search storytelling content by query."""
    from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort

    memory_store: MemoryStorePort = container.storage
    query = " ".join(args.query)
    items = memory_store.search_memory(query, project_id=args.project_id, top_k=20, tags=["story"])
    if not items:
        print("No results found.")
        return 0

    print(f"Search results ({len(items)}):")
    print(f"{'ID':38s}  {'Type':15s}  {'Preview'}")
    print("-" * 80)
    for item in items:
        item_type = _extract_type_from_tags(item.tags)
        preview = item.content.split("\n")[0][:50] if item.content else ""
        print(f"{item.id:38s}  {item_type:15s}  {preview}")
    return 0


def _cmd_story_persona(args: argparse.Namespace, container: CoreContainer) -> int:
    """Persona extraction subcommand."""
    persona_command = getattr(args, "persona_command", None)
    if persona_command == "extract":
        return _cmd_persona_extract(args, container)
    if persona_command == "status":
        return _cmd_persona_status(args, container)
    print("Usage: oc story persona <extract|status>")
    return 1


def _cmd_persona_extract(args: argparse.Namespace, container: CoreContainer) -> int:
    """Extract a persona from text."""
    from openchronicle.core.application.use_cases import run_task

    project_id = args.project_id
    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found.")
        return 1

    task = run_task.submit(
        container.orchestrator,
        project_id,
        "plugin.invoke",
        {
            "handler": "story.persona.extract",
            "input": {
                "character_name": args.name,
                "source_text": args.source_text,
            },
        },
    )

    try:
        result = asyncio.run(run_task.execute(container.orchestrator, task.id))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1

    result_data = result.result if hasattr(result, "result") else result
    if isinstance(result_data, str):
        result_data = json.loads(result_data)

    if isinstance(result_data, dict):
        status = result_data.get("status", "")
        if status == "not_available":
            print(f"Error: {result_data.get('error', '')}")
            return 1
        print(f"Persona extracted: {result_data.get('character_name', '')}")
        print(f"Confidence: {result_data.get('confidence', 0):.2f}")
        for field_name in ("physical_description", "voice_description", "mannerisms", "personality_traits"):
            val = result_data.get(field_name, "")
            if val:
                label = field_name.replace("_", " ").title()
                print(f"{label}: {val}")
    return 0


def _cmd_persona_status(args: argparse.Namespace, container: CoreContainer) -> int:
    """Show persona extraction capabilities."""
    from plugins.storytelling.application.persona_extractor import MULTIMODAL_REQUIRED_MESSAGE

    print("Persona Extraction Status")
    print("-" * 40)
    print("  Text:  READY")
    print("  Image: NOT AVAILABLE")
    print("  Voice: NOT AVAILABLE")
    print("  Video: NOT AVAILABLE")
    print(f"\n{MULTIMODAL_REQUIRED_MESSAGE}")
    return 0


def _cmd_story_consistency(args: argparse.Namespace, container: CoreContainer) -> int:
    """Check content for consistency against story context."""
    from openchronicle.core.application.use_cases import run_task

    project_id = args.project_id
    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found.")
        return 1

    content = " ".join(args.content)

    # Check if it looks like a memory ID (UUID-like)
    if len(content) == 36 and content.count("-") == 4:
        item = container.storage.get_memory(content)
        if item:
            content = item.content

    task = run_task.submit(
        container.orchestrator,
        project_id,
        "plugin.invoke",
        {
            "handler": "story.consistency.check",
            "input": {"content": content, "content_type": "scene"},
        },
    )

    try:
        result = asyncio.run(run_task.execute(container.orchestrator, task.id))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1

    result_data = result.result if hasattr(result, "result") else result
    if isinstance(result_data, str):
        result_data = json.loads(result_data)

    if isinstance(result_data, dict):
        passed = result_data.get("passed", True)
        issues = result_data.get("issues", [])
        summary = result_data.get("summary", "")

        status = "PASSED" if passed else "ISSUES FOUND"
        print(f"Consistency Check: {status}")
        if summary:
            print(f"Summary: {summary}")
        if issues:
            print(f"\nIssues ({len(issues)}):")
            for issue in issues:
                sev = issue.get("severity", "info").upper()
                desc = issue.get("description", "")
                print(f"  [{sev}] {desc}")
    return 0


def _cmd_story_emotion(args: argparse.Namespace, container: CoreContainer) -> int:
    """Analyze emotional arc in content."""
    from openchronicle.core.application.use_cases import run_task

    project_id = args.project_id
    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found.")
        return 1

    content = " ".join(args.content)
    character_names = None
    if getattr(args, "characters", None):
        character_names = [c.strip() for c in args.characters.split(",")]

    # Check if it looks like a memory ID
    if len(content) == 36 and content.count("-") == 4:
        item = container.storage.get_memory(content)
        if item:
            content = item.content

    task = run_task.submit(
        container.orchestrator,
        project_id,
        "plugin.invoke",
        {
            "handler": "story.emotion.analyze",
            "input": {"scene_text": content, "character_names": character_names},
        },
    )

    try:
        result = asyncio.run(run_task.execute(container.orchestrator, task.id))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1

    result_data = result.result if hasattr(result, "result") else result
    if isinstance(result_data, str):
        result_data = json.loads(result_data)

    if isinstance(result_data, dict):
        arc = result_data.get("arc_summary", "")
        beats = result_data.get("beats", [])
        loops = result_data.get("loops", [])

        print("Emotional Analysis")
        if arc:
            print(f"Arc: {arc}")
        if beats:
            print(f"\nBeats ({len(beats)}):")
            for b in beats:
                print(
                    f"  {b.get('character_name', '?')}: {b.get('emotion', '?')} "
                    f"(intensity: {b.get('intensity', 0):.1f}, {b.get('scene_position', '?')})"
                )
        if loops:
            print(f"\nLoops detected ({len(loops)}):")
            for l_item in loops:
                print(
                    f"  {l_item.get('character_name', '?')}: {l_item.get('emotion', '?')} "
                    f"({l_item.get('occurrence_count', 0)} times)"
                )
    return 0


def _cmd_story_bookmark(args: argparse.Namespace, container: CoreContainer) -> int:
    """Bookmark management subcommand."""
    bm_command = getattr(args, "bookmark_command", None)
    if bm_command == "create":
        return _cmd_bookmark_create(args, container)
    if bm_command == "list":
        return _cmd_bookmark_list(args, container)
    print("Usage: oc story bookmark <create|list>")
    return 1


def _cmd_bookmark_create(args: argparse.Namespace, container: CoreContainer) -> int:
    """Create a bookmark."""
    from openchronicle.core.application.use_cases import run_task

    project_id = args.project_id
    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found.")
        return 1

    task = run_task.submit(
        container.orchestrator,
        project_id,
        "plugin.invoke",
        {
            "handler": "story.bookmark.create",
            "input": {
                "label": args.label,
                "bookmark_type": args.type,
                "scene_id": getattr(args, "scene_id", None),
                "chapter": getattr(args, "chapter", None),
            },
        },
    )

    try:
        result = asyncio.run(run_task.execute(container.orchestrator, task.id))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1

    result_data = result.result if hasattr(result, "result") else result
    if isinstance(result_data, str):
        result_data = json.loads(result_data)

    if isinstance(result_data, dict):
        print(f"Bookmark created: {result_data.get('label', '')} (id: {result_data.get('id', '')})")
    return 0


def _cmd_bookmark_list(args: argparse.Namespace, container: CoreContainer) -> int:
    """List bookmarks."""
    from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort
    from plugins.storytelling.application.bookmark_manager import list_bookmarks
    from plugins.storytelling.domain.timeline import BookmarkType

    memory_store: MemoryStorePort = container.storage

    def _search(query: str, top_k: int = 8, tags: list[str] | None = None) -> list:
        return memory_store.search_memory(query, project_id=args.project_id, top_k=top_k, tags=tags)

    bm_type = None
    if getattr(args, "type", None):
        with contextlib.suppress(ValueError):
            bm_type = BookmarkType(args.type)

    bookmarks = list_bookmarks(_search, bm_type)
    if not bookmarks:
        print("No bookmarks found.")
        return 0

    print(f"Bookmarks ({len(bookmarks)}):")
    print(f"{'ID':38s}  {'Type':10s}  {'Chapter':15s}  {'Label'}")
    print("-" * 90)
    for bm in bookmarks:
        print(f"{bm.id:38s}  {bm.bookmark_type.value:10s}  {(bm.chapter or '-'):15s}  {bm.label}")
    return 0


def _cmd_story_timeline(args: argparse.Namespace, container: CoreContainer) -> int:
    """Show story timeline."""
    from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort
    from plugins.storytelling.application.timeline_assembler import assemble_timeline

    memory_store: MemoryStorePort = container.storage

    def _search(query: str, top_k: int = 8, tags: list[str] | None = None) -> list:
        return memory_store.search_memory(query, project_id=args.project_id, top_k=top_k, tags=tags)

    chapter_filter = getattr(args, "chapter", None)
    timeline = assemble_timeline(_search, chapter_filter)

    if not timeline.entries:
        print("No timeline entries found.")
        return 0

    print(f"Timeline ({len(timeline.entries)} entries):")
    for chapter_name, entries in timeline.chapters.items():
        print(f"\n  {chapter_name}")
        print(f"  {'-' * 40}")
        for entry in entries:
            marker = "S" if entry.entry_type == "scene" else "B"
            print(f"    [{marker}] {entry.label[:60]}")
    return 0


def _cmd_story_roll(args: argparse.Namespace, container: CoreContainer) -> int:
    """Roll dice using standard notation."""
    from plugins.storytelling.application.dice_engine import roll_notation

    try:
        result = roll_notation(
            args.notation,
            advantage=args.advantage,
            disadvantage=args.disadvantage,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    rolls_str = ", ".join(str(r) for r in result.rolls)
    mod_str = (
        f" + {result.modifier}"
        if result.modifier > 0
        else (f" - {abs(result.modifier)}" if result.modifier < 0 else "")
    )
    adv_str = " (advantage)" if result.advantage else (" (disadvantage)" if result.disadvantage else "")

    print(f"Rolling {args.notation}{adv_str}:")
    print(f"  Rolls: [{rolls_str}]{mod_str}")
    print(f"  Total: {result.total}")
    return 0


def _cmd_story_resolve(args: argparse.Namespace, container: CoreContainer) -> int:
    """Roll + difficulty check + optional stat modifier."""
    from plugins.storytelling.application.resolution import resolve_action
    from plugins.storytelling.application.stat_manager import (
        get_stat_modifier_for_resolution,
        load_stat_block,
    )
    from plugins.storytelling.domain.mechanics import DifficultyLevel, ResolutionType

    try:
        resolution_type = ResolutionType(args.resolution_type.lower())
    except ValueError:
        valid = ", ".join(r.value for r in ResolutionType)
        print(f"Error: Invalid resolution type. Valid: {valid}")
        return 1

    try:
        difficulty = DifficultyLevel[args.difficulty.upper()]
    except KeyError:
        valid = ", ".join(d.name.lower() for d in DifficultyLevel)
        print(f"Error: Invalid difficulty. Valid: {valid}")
        return 1

    char_modifier = 0
    if args.character:
        if not args.project_id:
            print("Error: --project-id required when using --character")
            return 1
        from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort

        memory_store: MemoryStorePort = container.storage

        def _search(query: str, top_k: int = 8, tags: list[str] | None = None) -> list:
            return memory_store.search_memory(query, project_id=args.project_id, top_k=top_k, tags=tags)

        stat_block = load_stat_block(_search, args.character)
        if stat_block:
            char_modifier = get_stat_modifier_for_resolution(stat_block, resolution_type)
            print(f"Character modifier ({args.character}): {char_modifier:+d}")
        else:
            print(f"No stat block found for {args.character}, rolling without modifier.")

    result = resolve_action(
        resolution_type,
        difficulty,
        char_modifier,
        advantage=args.advantage,
        disadvantage=args.disadvantage,
    )

    rolls_str = ", ".join(str(r) for r in result.dice_roll.rolls)
    print(f"\nResolution: {result.resolution_type.value}")
    print(f"Difficulty: {args.difficulty} (DC {result.difficulty_check})")
    print(f"Roll: [{rolls_str}] + {result.dice_roll.modifier} = {result.dice_roll.total}")
    print(f"Outcome: {result.outcome.value} (margin: {result.success_margin:+d})")
    return 0


def _cmd_story_stats(args: argparse.Namespace, container: CoreContainer) -> int:
    """Show a character's stat block."""
    from openchronicle.core.domain.ports.memory_store_port import MemoryStorePort
    from plugins.storytelling.application.stat_manager import load_stat_block
    from plugins.storytelling.domain.stats import STAT_CATEGORIES

    memory_store: MemoryStorePort = container.storage

    def _search(query: str, top_k: int = 8, tags: list[str] | None = None) -> list:
        return memory_store.search_memory(query, project_id=args.project_id, top_k=top_k, tags=tags)

    stat_block = load_stat_block(_search, args.character)
    if stat_block is None:
        print(f"No stat block found for {args.character}.")
        return 0

    print(f"Character Stats: {args.character}")
    print("-" * 40)
    for category, stat_types in STAT_CATEGORIES.items():
        print(f"\n  {category.value.upper()}")
        for st in stat_types:
            val = stat_block.values.get(st.value, 10)
            mod = stat_block.modifier(st)
            print(f"    {st.value:15s}  {val:2d}  ({mod:+d})")
    return 0


def _cmd_story_stats_set(args: argparse.Namespace, container: CoreContainer) -> int:
    """Set a character stat value."""
    from openchronicle.core.application.use_cases import run_task

    project_id = args.project_id
    project = container.storage.get_project(project_id)
    if project is None:
        print(f"Error: Project '{project_id}' not found.")
        return 1

    task = run_task.submit(
        container.orchestrator,
        project_id,
        "plugin.invoke",
        {
            "handler": "story.stats.set",
            "input": {
                "character_name": args.character,
                "stat": args.stat,
                "value": args.value,
                "reason": args.reason,
            },
        },
    )

    try:
        result = asyncio.run(run_task.execute(container.orchestrator, task.id))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1

    result_data = result.result if hasattr(result, "result") else result
    if isinstance(result_data, str):
        result_data = json.loads(result_data)

    if isinstance(result_data, dict):
        print(f"Updated {args.character}: {args.stat} = {result_data.get('value', args.value)}")
    else:
        print(f"Result: {result_data}")
    return 0

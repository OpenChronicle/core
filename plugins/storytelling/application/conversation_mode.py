"""Story mode prompt builder for conversation integration.

When a conversation's mode is set to ``"story"``, this builder is invoked
by ``prepare_ask()`` to produce a rich system prompt containing characters,
style guides, locations, and other storytelling context assembled from
project memory.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..application.context_assembler import assemble_story_context
from ..domain.modes import EngagementMode, build_system_prompt

logger = logging.getLogger(__name__)


def story_prompt_builder(
    prompt_text: str,
    *,
    memory_search: Callable[..., list[Any]],
    project_id: str | None = None,
) -> str:
    """Build a storytelling system prompt from project memory.

    Retrieves storytelling context (characters, style guide, locations, etc.)
    via tag-filtered memory search, then assembles the full system prompt
    using the existing ``build_system_prompt()`` pipeline.

    Defaults to director engagement mode and canon=True for conversation mode.
    """
    ctx = assemble_story_context(memory_search, prompt_text)

    if ctx.total_items == 0:
        logger.warning("Story mode active but no storytelling content found in memory")

    return build_system_prompt(
        EngagementMode.DIRECTOR,
        instructions=ctx.instructions,
        style_guide=ctx.style_guide,
        characters=ctx.characters,
        locations=ctx.locations,
        scenes=ctx.scenes,
        worldbuilding=ctx.worldbuilding,
        canon=True,
    )

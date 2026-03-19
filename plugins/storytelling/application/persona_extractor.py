"""Persona extraction — stub + text-only fallback.

Full multimodal extraction (image, voice, video) is deferred until
core Phase 6 (multimodal conversation input via asset system).
Non-text sources return an error with a clear message.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..domain.persona import ExtractedPersona, PersonaExtractionStatus, PersonaSource

logger = logging.getLogger(__name__)

MULTIMODAL_REQUIRED_MESSAGE = (
    "Multimodal persona extraction (image, voice, video) requires "
    "the core multimodal conversation input feature (Phase 6). "
    "Currently only text-based extraction is supported."
)

PERSONA_TAGS = ["story", "persona"]


async def extract_persona(
    memory_search: Any,
    memory_save: Any,
    llm_complete: Any,
    character_name: str,
    sources: list[PersonaSource],
) -> dict[str, Any]:
    """Extract a persona from provided sources.

    Non-text sources are rejected with MULTIMODAL_REQUIRED_MESSAGE.
    Text sources are processed via LLM extraction.

    Returns a dict with the extraction result or error.
    """
    non_text = [s for s in sources if s.source_type != "text"]
    if non_text:
        return {
            "status": PersonaExtractionStatus.NOT_AVAILABLE.value,
            "error": MULTIMODAL_REQUIRED_MESSAGE,
            "unsupported_sources": [s.source_type for s in non_text],
        }

    # Combine text sources
    text_content = "\n\n".join(s.content_ref for s in sources if s.source_type == "text")

    persona = await extract_persona_from_text(llm_complete, character_name, text_content)

    # Save to memory
    content = _format_persona_content(persona)
    saved = memory_save(content=content, tags=PERSONA_TAGS)

    return {
        "status": PersonaExtractionStatus.COMPLETED.value,
        "character_name": persona.character_name,
        "physical_description": persona.physical_description,
        "voice_description": persona.voice_description,
        "mannerisms": persona.mannerisms,
        "personality_traits": persona.personality_traits,
        "confidence": persona.confidence,
        "memory_id": saved.id,
    }


async def extract_persona_from_text(
    llm_complete: Any,
    character_name: str,
    text_content: str,
    *,
    temperature: float = 0.3,
) -> ExtractedPersona:
    """Extract a persona profile from text using LLM.

    Args:
        llm_complete: Handler context's llm_complete closure.
        character_name: Name of the character to extract.
        text_content: Text content describing the character.
        temperature: LLM temperature (low for precision).
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a character analyst for an interactive story. "
                "Extract a detailed persona profile from the provided text. "
                "Return ONLY valid JSON with these fields:\n"
                '"physical_description": appearance, build, distinguishing features\n'
                '"voice_description": speech patterns, tone, accent\n'
                '"mannerisms": habitual gestures, behaviors, tics\n'
                '"personality_traits": core personality characteristics\n'
                '"confidence": 0.0-1.0 how confident you are in the extraction\n'
            ),
        },
        {
            "role": "user",
            "content": f"Extract persona for: {character_name}\n\nSource text:\n{text_content}",
        },
    ]

    response = await llm_complete(messages, max_output_tokens=1024, temperature=temperature)

    return _parse_persona_response(character_name, response.content)


def _parse_persona_response(character_name: str, content: str) -> ExtractedPersona:
    """Parse LLM response into ExtractedPersona."""
    content = content.strip()

    if content.startswith("```"):
        lines = content.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse persona extraction JSON response")
        return ExtractedPersona(character_name=character_name)

    if not isinstance(data, dict):
        return ExtractedPersona(character_name=character_name)

    confidence = float(data.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))

    return ExtractedPersona(
        character_name=character_name,
        physical_description=str(data.get("physical_description", "")),
        voice_description=str(data.get("voice_description", "")),
        mannerisms=str(data.get("mannerisms", "")),
        personality_traits=str(data.get("personality_traits", "")),
        confidence=confidence,
    )


def _format_persona_content(persona: ExtractedPersona) -> str:
    """Format persona as memory content."""
    lines = [
        f"[Persona] {persona.character_name}",
        f"Confidence: {persona.confidence:.2f}",
        "",
    ]
    if persona.physical_description:
        lines.append(f"Physical: {persona.physical_description}")
    if persona.voice_description:
        lines.append(f"Voice: {persona.voice_description}")
    if persona.mannerisms:
        lines.append(f"Mannerisms: {persona.mannerisms}")
    if persona.personality_traits:
        lines.append(f"Traits: {persona.personality_traits}")
    return "\n".join(lines)

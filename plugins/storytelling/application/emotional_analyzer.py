"""LLM-based emotional arc analysis for storytelling scenes.

Analyzes emotional beats per character, detects repetitive loops,
and tracks emotional arcs across scenes.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EmotionLabel(Enum):
    """Core emotion labels (Plutchik's wheel simplified)."""

    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class EmotionalBeat:
    """A single emotional moment for a character."""

    character_name: str
    emotion: EmotionLabel
    intensity: float  # 0.0 to 1.0
    trigger: str
    scene_position: str  # "early", "middle", "late"


@dataclass(frozen=True)
class EmotionalLoop:
    """Detected repetitive emotional pattern."""

    character_name: str
    emotion: EmotionLabel
    occurrence_count: int
    confidence: float  # 0.0 to 1.0


@dataclass
class EmotionalReport:
    """Full emotional analysis report."""

    beats: list[EmotionalBeat] = field(default_factory=list)
    loops: list[EmotionalLoop] = field(default_factory=list)
    arc_summary: str = ""
    character_arcs: dict[str, list[EmotionalBeat]] = field(default_factory=dict)


async def analyze_emotional_arc(
    memory_search: Any,
    llm_complete: Any,
    scene_text: str,
    character_names: list[str] | None = None,
    *,
    temperature: float = 0.3,
) -> EmotionalReport:
    """Analyze emotional arc in a scene using LLM.

    1. Search recent scenes for emotional context
    2. Ask LLM to analyze emotional beats
    3. Run loop detection on results

    Args:
        memory_search: Handler context's memory_search closure.
        llm_complete: Handler context's llm_complete closure.
        scene_text: Scene content to analyze.
        character_names: Optional list of characters to focus on.
        temperature: LLM temperature.
    """
    # 1. Get prior emotional context
    prior_beats: list[EmotionalBeat] = []
    prior_scenes = memory_search("scene emotion", top_k=5, tags=["story", "scene"])
    # We don't re-analyze prior scenes — just pass them as context

    # 2. Build LLM prompt
    chars_str = ", ".join(character_names) if character_names else "all characters in the scene"
    prior_context = ""
    if prior_scenes:
        snippets = [item.content[:200] for item in prior_scenes[:3]]
        prior_context = f"\nRecent scenes for context:\n{'---'.join(snippets)}\n"

    prompt = (
        f"Analyze the emotional content of this scene for: {chars_str}\n"
        f"{prior_context}\n"
        f"Scene:\n{scene_text}\n\n"
        "Return a JSON object with:\n"
        '- "beats": array of {"character_name": "...", "emotion": "<one of: '
        "joy, sadness, anger, fear, surprise, disgust, trust, anticipation, neutral>"
        '", "intensity": 0.0-1.0, "trigger": "...", "scene_position": "early|middle|late"}\n'
        '- "arc_summary": brief overall emotional arc description\n'
        "Return ONLY valid JSON."
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an emotional analysis engine for interactive storytelling. "
                "Identify emotional beats for each character, noting what triggers "
                "each emotional shift and its intensity. Return ONLY valid JSON."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = await llm_complete(messages, max_output_tokens=1024, temperature=temperature)

    # 3. Parse response
    beats, arc_summary = _parse_emotional_response(response.content)

    # 4. Detect loops
    loops = detect_emotional_loops(beats, prior_beats)

    # 5. Group by character
    character_arcs: dict[str, list[EmotionalBeat]] = {}
    for beat in beats:
        if beat.character_name not in character_arcs:
            character_arcs[beat.character_name] = []
        character_arcs[beat.character_name].append(beat)

    return EmotionalReport(
        beats=beats,
        loops=loops,
        arc_summary=arc_summary,
        character_arcs=character_arcs,
    )


def detect_emotional_loops(
    current_beats: list[EmotionalBeat],
    prior_beats: list[EmotionalBeat],
    threshold: int = 3,
) -> list[EmotionalLoop]:
    """Detect repetitive emotional patterns across beats.

    Pure function, no LLM. Looks for the same character+emotion
    appearing >= threshold times across current and prior beats.
    """
    combined = list(prior_beats) + list(current_beats)

    # Count character+emotion occurrences
    counts: dict[tuple[str, EmotionLabel], int] = {}
    for beat in combined:
        key = (beat.character_name, beat.emotion)
        counts[key] = counts.get(key, 0) + 1

    loops = []
    total = len(combined) if combined else 1
    for (char, emotion), count in counts.items():
        if count >= threshold:
            confidence = min(1.0, count / total)
            loops.append(
                EmotionalLoop(
                    character_name=char,
                    emotion=emotion,
                    occurrence_count=count,
                    confidence=confidence,
                )
            )
    return loops


def _parse_emotional_response(content: str) -> tuple[list[EmotionalBeat], str]:
    """Parse LLM response into emotional beats."""
    content = content.strip()

    # Handle markdown code fences
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse emotional analysis JSON response")
        return [], ""

    if not isinstance(data, dict):
        return [], ""

    beats = []
    for item in data.get("beats", []):
        if isinstance(item, dict):
            try:
                emotion = EmotionLabel(item.get("emotion", "neutral").lower())
            except ValueError:
                emotion = EmotionLabel.NEUTRAL

            intensity = float(item.get("intensity", 0.5))
            intensity = max(0.0, min(1.0, intensity))

            beats.append(
                EmotionalBeat(
                    character_name=str(item.get("character_name", "")),
                    emotion=emotion,
                    intensity=intensity,
                    trigger=str(item.get("trigger", "")),
                    scene_position=str(item.get("scene_position", "middle")),
                )
            )

    arc_summary = str(data.get("arc_summary", ""))
    return beats, arc_summary

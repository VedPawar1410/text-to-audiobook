"""How directed lines become engine settings and silence.

Numbers come from docs/narration-guide.md. Pure functions: no audio, no database.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Protocol

from app.director.vocabulary import EMOTIONS
from app.render.speech import speech_text

INTENSITY_FACTOR = {1: 0.5, 2: 1.0, 3: 1.4}
PACE_FACTOR = {"slow": 0.92, "normal": 1.0, "fast": 1.08}
MIN_SPEED, MAX_SPEED = 0.75, 1.25  # beyond this Kokoro stops sounding natural

PARAGRAPH_GAP_MS = {"prose": 450, "screenplay": 350}
GAP_BEFORE_KIND_MS = {"heading": 700, "scene_heading": 900}
SCENE_BREAK_MS = 1500
TRANSITION_MS = 1200
CHAPTER_TAIL_MS = 1200  # silence at the end of each chapter file

FALLBACK_VOICE = ("am_michael", 1.0)


class SegmentLike(Protocol):
    id: int
    block_index: int
    block_kind: str
    text: str
    role: str
    emotion: str
    intensity: int
    pace: str
    pause_before_ms: int
    pause_after_ms: int


@dataclass(frozen=True)
class Step:
    """One line of a chapter, ready to render."""

    segment_id: int
    silence_before_ms: int
    speech: str | None  # None: a silent beat (scene break, transition)
    silent_ms: int = 0  # length of that beat
    voice: str = ""
    speed: float = 1.0


def speed_for(emotion: str, intensity: int, pace: str, persona_speed: float) -> float:
    """Persona speed x emotion (scaled by intensity) x pace, clamped and rounded.

    Rounding to 0.01 also means near-identical lines share cached clips.
    """
    base = EMOTIONS.get(emotion, EMOTIONS["neutral"]).speed
    emotion_factor = 1 + (base - 1) * INTENSITY_FACTOR.get(intensity, 1.0)
    speed = persona_speed * emotion_factor * PACE_FACTOR.get(pace, 1.0)
    return round(min(MAX_SPEED, max(MIN_SPEED, speed)), 2)


def _structural_gap(previous: SegmentLike | None, segment: SegmentLike, document_format: str) -> int:
    if previous is None or segment.block_index == previous.block_index:
        return 0  # chapter start, or the next sentence of the same paragraph/speech
    return GAP_BEFORE_KIND_MS.get(segment.block_kind, PARAGRAPH_GAP_MS.get(document_format, 450))


def plan_chapter(
    segments: list[SegmentLike], voices: dict[str, tuple[str, float]], document_format: str
) -> list[Step]:
    """voices maps a role (NARRATOR, KANG…) to (voice id, persona speed)."""
    steps: list[Step] = []
    previous: SegmentLike | None = None

    for segment in segments:
        gap = max(previous.pause_after_ms if previous else 0, _structural_gap(previous, segment, document_format))
        silence_before = gap + segment.pause_before_ms
        spoken = speech_text(segment.block_kind, segment.text)

        if spoken is None:
            beat = SCENE_BREAK_MS if segment.block_kind == "scene_break" else TRANSITION_MS
            steps.append(Step(segment.id, silence_before, None, silent_ms=beat))
        else:
            voice, persona_speed = voices.get(segment.role) or voices.get("NARRATOR") or FALLBACK_VOICE
            speed = speed_for(segment.emotion, segment.intensity, segment.pace, persona_speed)
            steps.append(Step(segment.id, silence_before, spoken, voice=voice, speed=speed))
        previous = segment

    return steps


def fingerprint(steps: list[Step]) -> str:
    """Changes whenever anything that affects the chapter's audio changes."""
    return hashlib.sha256(json.dumps([asdict(s) for s in steps]).encode()).hexdigest()[:16]

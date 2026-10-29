"""The AI director, in two passes.

A. direct_document: one call reads the whole text (Gemini Flash takes 1M tokens)
   and decides the genre, a summary, the narrator's style and the cast.
B. direct_lines: every sentence gets a performance (speaker, emotion, pace, pauses,
   emphasis). Chunks run in parallel; each also sees the few lines before it.

The LLM proposes and our code decides: speakers the parser already knows always
win, values are clamped to safe ranges, and lines the LLM skipped get defaults.
"""

import logging
import string
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.director.prompts import SYSTEM, document_prompt, lines_prompt
from app.director.schema import CastMember, DocumentDirection, LineDirection, LineDirections
from app.llm import LLM, LLMError

log = logging.getLogger(__name__)

NARRATOR = "NARRATOR"
NARRATED_KINDS = {"heading", "scene_heading", "transition", "action", "scene_break"}
CHUNK_LINES = 150
CONTEXT_LINES = 6
PARALLEL_CALLS = 3  # free-tier rate limits are low; more parallelism mostly buys 429s
MAX_PAUSE_MS = 3000


@dataclass(frozen=True)
class Line:
    """One sentence with its structural context, as the director sees it."""

    index: int
    kind: str
    text: str
    speaker: str | None = None  # known from the parser (screenplays)
    direction: str | None = None  # e.g. "quietly"


@dataclass(frozen=True)
class Performance:
    index: int
    role: str  # NARRATOR or a cast id
    emotion: str
    intensity: int
    pace: str
    pause_before_ms: int
    pause_after_ms: int
    emphasis: list[str]
    labelled: bool  # False when the LLM skipped the line and defaults were used


def direct_document(llm: LLM, *, title: str | None, format: str, speakers: list[str], lines: list[Line]) -> DocumentDirection:
    spoken = [line for line in lines if line.text]
    direction = llm.generate_json(
        system=SYSTEM,
        prompt=document_prompt(title=title, format=format, speakers=speakers, lines=spoken),
        schema=DocumentDirection,
    )
    for member in direction.cast:
        member.id = member.id.strip().upper()
    # The parser's speakers are facts: every one of them needs a cast entry
    known = {member.id for member in direction.cast}
    for speaker in speakers:
        if speaker not in known:
            direction.cast.append(
                CastMember(
                    id=speaker,
                    display_name=speaker.title(),
                    gender="unknown",
                    age="adult",
                    accent="any",
                    voice_description="a distinct supporting voice",
                )
            )
    return direction


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _resolve(line: Line, label: LineDirection | None, cast_ids: set[str]) -> Performance:
    if line.speaker:
        role = line.speaker
    elif line.kind in NARRATED_KINDS or label is None:
        role = NARRATOR
    else:
        proposed = label.speaker.strip().upper()
        role = proposed if proposed in cast_ids else NARRATOR

    if label is None or not line.text:
        return Performance(line.index, role, "neutral", 1, "normal", 0, 0, [], labelled=not line.text)

    words = {w.strip(string.punctuation).lower() for w in line.text.split()}
    emphasis = [w for w in label.emphasis if w.strip(string.punctuation).lower() in words][:2]
    return Performance(
        index=line.index,
        role=role,
        emotion=label.emotion,
        intensity=_clamp(label.intensity, 1, 3),
        pace=label.pace,
        pause_before_ms=_clamp(label.pause_before_ms, 0, MAX_PAUSE_MS),
        pause_after_ms=_clamp(label.pause_after_ms, 0, MAX_PAUSE_MS),
        emphasis=emphasis,
        labelled=True,
    )


def direct_lines(llm: LLM, direction: DocumentDirection, lines: list[Line]) -> list[Performance]:
    spoken = [line for line in lines if line.text]
    chunks = [spoken[i : i + CHUNK_LINES] for i in range(0, len(spoken), CHUNK_LINES)]

    def label_chunk(number: int) -> list[LineDirection]:
        start = number * CHUNK_LINES
        context = spoken[max(0, start - CONTEXT_LINES) : start]
        try:
            prompt = lines_prompt(direction, context, chunks[number])
            return llm.generate_json(system=SYSTEM, prompt=prompt, schema=LineDirections).lines
        except LLMError as error:
            # One failed chunk shouldn't sink a whole book: its lines fall back to defaults
            log.warning("Chunk %d of %d failed: %s", number + 1, len(chunks), error)
            return []

    with ThreadPoolExecutor(PARALLEL_CALLS) as pool:
        results = list(pool.map(label_chunk, range(len(chunks))))

    if spoken and not any(results):
        raise LLMError("The AI director couldn't label any lines. Please try again.")

    labels = {label.index: label for result in results for label in result}
    cast_ids = {member.id for member in direction.cast}
    return [_resolve(line, labels.get(line.index), cast_ids) for line in lines]

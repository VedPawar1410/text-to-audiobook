"""The AI director, in two passes.

A. direct_document: one call reads the whole text (Gemini Flash takes 1M tokens)
   and decides the genre, a summary, the narrator's style and the cast.
B. direct_lines: every sentence gets a performance (speaker, emotion, pace, pauses,
   emphasis). Chunks run in parallel; each also sees the few lines before it. Chunks
   that fail get one more try at the end, one at a time, when the service is quieter.

The LLM proposes and our code decides: speakers the parser already knows always
win, values are clamped to safe ranges, and lines the LLM skipped get defaults.
"""

import logging
import string
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from pydantic import ValidationError

from app.director.prompts import SYSTEM, document_prompt, lines_prompt
from app.director.schema import CastMember, DocumentDirection, LineDirection
from app.llm import LLM, LLMError

log = logging.getLogger(__name__)

NARRATOR = "NARRATOR"
NARRATED_KINDS = {"heading", "scene_heading", "transition", "action", "scene_break"}
CHUNK_LINES = 150  # a provider without its own batch_lines (the test fakes)
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


def parse_rows(text: str) -> list[LineDirection]:
    """The model's rows, like `12|MARA|anxious|2|fast|200|300|ship`, as validated labels.

    Rows instead of JSON: ~23 output tokens a line against ~80 (Gemini pretty-prints JSON,
    and the whitespace is tokens too; measured in PR 16). A row that doesn't parse is
    skipped: its line gets the default delivery and is counted in the document's warning.
    """
    labels = []
    for row in text.splitlines():
        parts = [part.strip() for part in row.strip().strip("`").split("|")]
        if len(parts) < 7:
            continue
        try:
            labels.append(
                LineDirection(
                    index=int(parts[0].strip("[]")),
                    speaker=parts[1].upper(),
                    emotion=parts[2].lower(),
                    intensity=int(parts[3]),
                    pace=parts[4].lower(),
                    pause_before_ms=int(parts[5]),
                    pause_after_ms=int(parts[6]),
                    emphasis=[word.strip() for word in "|".join(parts[7:]).split(",") if word.strip()],
                )
            )
        except (ValueError, ValidationError):
            continue
    return labels


# (stage, done, total): "labelling" chunk by chunk, then "retrying" any that failed
Progress = Callable[[str, int, int], None]


def direct_lines(
    llm: LLM,
    direction: DocumentDirection,
    lines: list[Line],
    on_progress: Progress | None = None,
    fallback: LLM | None = None,
) -> list[Performance]:
    """Label every spoken line, in chunks, on the light models.

    Each provider says how many lines it takes per request and how many requests at once
    (Groq's free tier allows 8k tokens a minute, so: fewer lines, one at a time).
    Chunks that fail (usually a busy service, after its own retries) get one more try:
    on the fallback provider when there is one, otherwise on the same LLM.
    """
    size = getattr(llm, "batch_lines", CHUNK_LINES)
    spoken = [line for line in lines if line.text]
    chunks = [spoken[i : i + size] for i in range(0, len(spoken), size)]
    report = on_progress or (lambda stage, done, total: None)
    finished = 0
    counter = threading.Lock()

    def label(batch: list[Line], start: int, client: LLM, light: bool) -> list[LineDirection]:
        context = spoken[max(0, start - CONTEXT_LINES) : start]
        prompt = lines_prompt(direction, context, batch)
        labels = parse_rows(client.generate_text(system=SYSTEM, prompt=prompt, light=light))
        if not labels:
            raise LLMError("The answer had no usable rows.")
        return labels

    def label_chunk(number: int) -> list[LineDirection]:
        try:
            return label(chunks[number], number * size, llm, light=True)
        except LLMError as error:
            # One failed chunk shouldn't sink a whole book: its lines fall back to defaults
            log.warning("Chunk %d of %d failed: %s", number + 1, len(chunks), error)
            return []

    def label_on_fallback(number: int) -> list[LineDirection]:
        start, step = number * size, getattr(fallback, "batch_lines", CHUNK_LINES)
        labelled: list[LineDirection] = []
        for offset in range(0, len(chunks[number]), step):
            piece = chunks[number][offset : offset + step]
            try:
                labelled += label(piece, start + offset, fallback, light=True)
            except LLMError as error:
                log.warning("Chunk %d failed on the fallback too: %s", number + 1, error)
        return labelled

    def label_and_count(number: int) -> list[LineDirection]:
        nonlocal finished
        result = label_chunk(number)
        with counter:  # chunks finish in any order, on pool threads
            finished += 1
            report("labelling", finished, len(chunks))
        return result

    report("labelling", 0, len(chunks))
    with ThreadPoolExecutor(getattr(llm, "parallel", PARALLEL_CALLS)) as pool:
        results = list(pool.map(label_and_count, range(len(chunks))))

    failed = [number for number, result in enumerate(results) if not result]
    for attempt, number in enumerate(failed):
        report("retrying", attempt, len(failed))
        results[number] = label_on_fallback(number) if fallback else label_chunk(number)

    if spoken and not any(results):
        raise LLMError("The AI director couldn't label any lines. Please try again.")

    labels = {label.index: label for result in results for label in result}
    cast_ids = {member.id for member in direction.cast}
    return [_resolve(line, labels.get(line.index), cast_ids) for line in lines]

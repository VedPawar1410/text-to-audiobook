"""Turn raw engine token timings into clean per-word timings for the read-along reader.

Pure functions (no model needed), so they're easy to test.
"""

from dataclasses import dataclass

import numpy as np

from app.tts.base import WordTiming


@dataclass(frozen=True)
class Token:
    text: str
    start: float | None  # engines sometimes leave a token untimed
    end: float | None
    whitespace: str  # what followed the token in the text: " " or ""


def merge_chunks(chunks: list[tuple[list[Token], float]]) -> list[WordTiming]:
    """Merge (tokens, chunk_duration_seconds) chunks into one list of words.

    - Long text comes back in several chunks, each timed from 0, so each chunk is
      shifted by the total duration of the chunks before it.
    - A token is glued onto the previous one when no whitespace separated them
      ("ends" + "." -> "ends."), so words match the original text split on spaces.
    """
    words: list[WordTiming] = []
    offset = 0.0

    for tokens, duration in chunks:
        glue = False  # never glue across a chunk boundary
        for tok in tokens:
            prev_end = words[-1].end if words else offset
            start = offset + tok.start if tok.start is not None else prev_end
            end = offset + tok.end if tok.end is not None else start

            if glue and words:
                last = words[-1]
                words[-1] = WordTiming(last.text + tok.text, last.start, max(last.end, end))
            else:
                words.append(WordTiming(tok.text, start, end))
            glue = tok.whitespace == ""
        offset += duration

    return words


def trim_to_speech(
    audio: np.ndarray,
    sample_rate: int,
    words: list[WordTiming],
    lead: float = 0.05,
    tail: float = 0.15,
) -> tuple[np.ndarray, list[WordTiming]]:
    """Cut the engine's built-in leading/trailing silence.

    Pauses are decided by the AI director and inserted by the assembler, so each
    clip should contain only speech (plus a tiny margin so nothing clips).
    """
    if not words:
        return audio, words

    start = max(0.0, words[0].start - lead)
    end = min(len(audio) / sample_rate, words[-1].end + tail)
    trimmed = audio[int(start * sample_rate) : int(end * sample_rate)]
    shifted = [WordTiming(w.text, w.start - start, w.end - start) for w in words]
    return trimmed, shifted

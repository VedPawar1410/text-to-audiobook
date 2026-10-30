"""Chapter audio: clips and silences laid end to end, streamed into an MP3, plus a
manifest of when every line and word is spoken (what the read-along follows).
"""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import numpy as np

from app.render.performance import CHAPTER_TAIL_MS, Step
from app.tts.base import RenderResult

SAMPLE_RATE = 24_000
GetClip = Callable[[str, str, float], RenderResult]
Write = Callable[[np.ndarray], None]


def _silence(ms: int, sample_rate: int) -> np.ndarray:
    return np.zeros(int(sample_rate * ms / 1000), dtype=np.float32)


def assemble(steps: list[Step], get_clip: GetClip, write: Write, sample_rate: int = SAMPLE_RATE) -> dict:
    """Stream the chapter to `write` piece by piece; return its manifest.

    Streaming matters: a 2.5-hour chapter is ~860 MB as float32 in memory.
    """
    position = 0  # in samples
    entries = []

    def add(chunk: np.ndarray) -> None:
        nonlocal position
        if len(chunk):
            write(chunk)
            position += len(chunk)

    for step in steps:
        add(_silence(step.silence_before_ms, sample_rate))
        start = position / sample_rate
        words = []
        if step.speech is None:
            add(_silence(step.silent_ms, sample_rate))
        else:
            clip = get_clip(step.speech, step.voice, step.speed)
            if clip.sample_rate != sample_rate:
                raise ValueError(f"Expected {sample_rate} Hz audio, got {clip.sample_rate} Hz")
            add(clip.audio.astype(np.float32))
            words = [
                {"text": w.text, "start": round(start + w.start, 3), "end": round(start + w.end, 3)}
                for w in clip.words
            ]
        entries.append(
            {"segment_id": step.segment_id, "start": round(start, 3), "end": round(position / sample_rate, 3), "words": words}
        )

    add(_silence(CHAPTER_TAIL_MS, sample_rate))
    return {"duration": round(position / sample_rate, 3), "segments": entries}


class Mp3Writer:
    """Pipes float samples into ffmpeg: mono 64 kbps MP3, about 29 MB per hour."""

    def __init__(self, path: Path, sample_rate: int = SAMPLE_RATE):
        self._path = path
        self._temporary = path.with_name(path.name + ".tmp")
        self._process = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(sample_rate), "-ac", "1",
             "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", str(self._temporary)],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )  # fmt: skip

    def write(self, chunk: np.ndarray) -> None:
        self._process.stdin.write(np.clip(chunk, -1, 1).astype("<f4").tobytes())

    def __enter__(self) -> "Mp3Writer":
        return self

    def __exit__(self, error_type, error, traceback) -> None:
        if error_type is not None:  # cancelled or failed: discard the partial file
            self._process.kill()
            self._process.wait()
            self._temporary.unlink(missing_ok=True)
            return
        self._process.stdin.close()
        if self._process.wait() != 0:
            raise RuntimeError(f"ffmpeg failed: {self._process.stderr.read().decode()[:300]}")
        os.replace(self._temporary, self._path)

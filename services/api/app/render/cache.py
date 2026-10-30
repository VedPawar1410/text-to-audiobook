"""Rendered clips on disk, keyed by everything that affects their sound.

Editing one line changes one key, so only that line is re-rendered. Identical
lines (same text, voice and speed) are rendered once, even across documents.
"""

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path

import soundfile as sf

from app.tts.base import RenderResult, TTSEngine, WordTiming


def atomic_write(path: Path, write: Callable[[Path], object]) -> None:
    """Write to a temp file, then rename: a killed render never leaves half a file."""
    temporary = path.with_name(path.name + ".tmp")
    write(temporary)
    os.replace(temporary, path)


class ClipCache:
    def __init__(self, directory: Path, engine: TTSEngine):
        directory.mkdir(parents=True, exist_ok=True)
        self._directory = directory
        self._engine = engine
        self.hits = 0
        self.misses = 0

    def key(self, text: str, voice: str, speed: float) -> str:
        return hashlib.sha256(f"{self._engine.name}|{voice}|{speed:.2f}|{text}".encode()).hexdigest()[:32]

    def get(self, text: str, voice: str, speed: float) -> RenderResult:
        key = self.key(text, voice, speed)
        audio_path = self._directory / f"{key}.flac"
        words_path = self._directory / f"{key}.json"

        if audio_path.exists() and words_path.exists():
            self.hits += 1
            audio, sample_rate = sf.read(audio_path, dtype="float32")
            words = [WordTiming(*w) for w in json.loads(words_path.read_text())["words"]]
            return RenderResult(audio, sample_rate, words)

        self.misses += 1
        result = self._engine.render(text, voice, speed)
        # FLAC: lossless and about half the size of WAV. Audio first, so a clip only
        # counts as cached once both files exist.
        atomic_write(audio_path, lambda p: sf.write(p, result.audio, result.sample_rate, format="FLAC", subtype="PCM_16"))
        words = [[w.text, w.start, w.end] for w in result.words]
        atomic_write(words_path, lambda p: p.write_text(json.dumps({"words": words})))
        return result

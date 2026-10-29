"""Engine-agnostic TTS types.

Every engine (Kokoro now; OpenAI / ElevenLabs later) returns the same RenderResult,
so the render pipeline and the read-along reader never care which engine ran.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class WordTiming:
    text: str  # the word as written, punctuation attached ("ends.")
    start: float  # seconds from the start of the clip
    end: float


@dataclass(frozen=True)
class Voice:
    id: str
    name: str
    gender: str  # "female" | "male"
    accent: str  # "American" | "British"


@dataclass(frozen=True)
class RenderResult:
    audio: np.ndarray  # mono float32 samples
    sample_rate: int
    words: list[WordTiming]

    @property
    def duration(self) -> float:
        return len(self.audio) / self.sample_rate


class TTSEngine(Protocol):
    name: str

    def voices(self) -> list[Voice]: ...

    def render(self, text: str, voice: str, speed: float = 1.0) -> RenderResult: ...

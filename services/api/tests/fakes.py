"""A stand-in for Gemini: same answers shape, no network, records every prompt."""

import re
import threading

import numpy as np

from app.director.schema import CastMember, DocumentDirection, LineDirection, LineDirections
from app.llm import LLMError
from app.tts.base import RenderResult, Voice, WordTiming


class FakeEngine:
    """Predictable audio: 0.2 s per word at speed 1. Records every render."""

    name = "fake"
    sample_rate = 24_000

    def __init__(self, fail_on: str | None = None):
        self.calls: list[tuple[str, str, float]] = []
        self.fail_on = fail_on

    def voices(self):
        return [Voice("am_michael", "Michael", "male", "American")]

    def render(self, text: str, voice: str, speed: float = 1.0) -> RenderResult:
        if self.fail_on and self.fail_on in text:
            raise RuntimeError("synthesis exploded")
        self.calls.append((text, voice, speed))
        per_word = 0.2 / speed
        words = text.split()
        audio = np.full(int(self.sample_rate * per_word * len(words)), 0.1, dtype=np.float32)
        timings = [WordTiming(w, i * per_word, (i + 1) * per_word) for i, w in enumerate(words)]
        return RenderResult(audio, self.sample_rate, timings)


def cast_member(id: str, gender: str = "male", age: str = "adult", accent: str = "american") -> CastMember:
    return CastMember(
        id=id, display_name=id.title(), gender=gender, age=age, accent=accent, voice_description="distinct"
    )


def direction(**overrides) -> DocumentDirection:
    values = dict(
        genre="screenplay",
        subgenre="superhero epic",
        summary="A conqueror waits at the end of time.",
        narrator_gender="male",
        narrator_accent="british",
        narrator_style="crisp and cinematic",
        cast=[cast_member("KANG"), cast_member("THOR")],
    )
    values.update(overrides)
    return DocumentDirection(**values)


def label(index: int, **overrides) -> LineDirection:
    values = dict(
        index=index, speaker="NARRATOR", emotion="neutral", intensity=1, pace="normal",
        pause_before_ms=0, pause_after_ms=250, emphasis=[],
    )  # fmt: skip
    values.update(overrides)
    return LineDirection(**values)


class FakeLLM:
    def __init__(self, document=None, labeller=label, skip=(), fail_chunks_starting_at=(), fail_document=False):
        self.document = document or direction()
        self.labeller = labeller
        self.skip = set(skip)
        self.fail_chunks = set(fail_chunks_starting_at)
        self.fail_document = fail_document
        self.prompts: list[str] = []
        self._lock = threading.Lock()  # chunks are labelled in parallel threads

    def generate_json(self, *, system, prompt, schema):
        with self._lock:
            self.prompts.append(prompt)
        if schema is DocumentDirection:
            if self.fail_document:
                raise LLMError("The AI service is unavailable right now.")
            return self.document.model_copy(deep=True)

        to_label = prompt.split("Label every one of these lines")[1]
        indices = [int(i) for i in re.findall(r"^\[(\d+)\]", to_label, re.MULTILINE)]
        if indices and indices[0] in self.fail_chunks:
            raise LLMError("busy")
        return LineDirections(lines=[self.labeller(i) for i in indices if i not in self.skip])

    @property
    def line_prompts(self) -> list[str]:
        return [p for p in self.prompts if "Label every one of these lines" in p]

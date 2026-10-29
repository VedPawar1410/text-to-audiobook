"""A stand-in for Gemini: same answers shape, no network, records every prompt."""

import re
import threading

from app.director.schema import CastMember, DocumentDirection, LineDirection, LineDirections
from app.llm import LLMError


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

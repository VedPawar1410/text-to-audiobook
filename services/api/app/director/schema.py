"""What the LLM must return. Gemini enforces these schemas (string enums only, so
intensity is a plain int that our code clamps to 1–3)."""

from typing import Literal

from pydantic import BaseModel

from app.director.vocabulary import EmotionName, GenreName

Gender = Literal["female", "male", "unknown"]
Age = Literal["child", "young", "adult", "elder"]
Accent = Literal["american", "british", "any"]
Pace = Literal["slow", "normal", "fast"]


class CastMember(BaseModel):
    id: str  # speaker id exactly as in the text, e.g. "KANG"
    display_name: str  # e.g. "Kang"
    gender: Gender
    age: Age
    accent: Accent
    voice_description: str  # e.g. "gravelly, menacing, slow and theatrical"


class DocumentDirection(BaseModel):
    genre: GenreName
    subgenre: str
    summary: str
    narrator_gender: Gender
    narrator_accent: Accent
    narrator_style: str
    cast: list[CastMember]


class LineDirection(BaseModel):
    index: int
    speaker: str  # "NARRATOR" or a cast id
    emotion: EmotionName
    intensity: int  # 1 subtle · 2 clear · 3 strong
    pace: Pace
    pause_before_ms: int
    pause_after_ms: int
    emphasis: list[str]


class LineDirections(BaseModel):
    lines: list[LineDirection]

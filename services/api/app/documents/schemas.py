import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.director.schema import Pace
from app.director.vocabulary import EmotionName


class DocumentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class PersonaUpdate(BaseModel):
    """Re-cast or tweak a cast member. Only the fields sent are changed."""

    voice: str | None = None
    speed: float | None = Field(default=None, ge=0.5, le=2.0)
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class SegmentUpdate(BaseModel):
    """Override the director on one line. Only the fields sent are changed."""

    role: str | None = None
    emotion: EmotionName | None = None
    intensity: int | None = Field(default=None, ge=1, le=3)
    pace: Pace | None = None
    pause_before_ms: int | None = Field(default=None, ge=0, le=3000)
    pause_after_ms: int | None = Field(default=None, ge=0, le=3000)


class PersonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cast_id: str
    display_name: str
    gender: str
    age: str
    accent: str
    description: str
    voice: str
    speed: float


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    block_index: int
    block_kind: str
    text: str
    speaker: str | None
    block_direction: str | None
    role: str
    emotion: str
    intensity: int
    pace: str
    pause_before_ms: int
    pause_after_ms: int
    emphasis: list[str]


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    title: str | None
    segments: list[SegmentOut]


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    format: str
    status: str
    error: str | None
    warning: str | None
    genre: str | None
    created_at: datetime
    stats: dict


class DocumentDetail(DocumentSummary):
    subgenre: str | None
    summary: str | None
    narrator_style: str | None
    personas: list[PersonaOut]
    sections: list[SectionOut]

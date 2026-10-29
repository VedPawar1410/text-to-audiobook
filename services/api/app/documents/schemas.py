import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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

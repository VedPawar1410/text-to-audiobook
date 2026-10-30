"""Database tables.

Created with create_all at startup; no migrations yet, because POC data is
disposable. Add Alembic once there's data worth keeping.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None]
    format: Mapped[str] = mapped_column(String(20))  # prose | screenplay
    status: Mapped[str] = mapped_column(String(20), default="parsed")  # parsed → directing → directed | failed
    error: Mapped[str | None] = mapped_column(Text)
    warning: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict] = mapped_column(JSONB)
    genre: Mapped[str | None] = mapped_column(String(30))
    subgenre: Mapped[str | None]
    summary: Mapped[str | None] = mapped_column(Text)
    narrator_style: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    sections: Mapped[list["Section"]] = relationship(
        back_populates="document", order_by="Section.position", cascade="all, delete-orphan"
    )
    segments: Mapped[list["Segment"]] = relationship(
        back_populates="document", order_by="Segment.position", cascade="all, delete-orphan"
    )
    personas: Mapped[list["Persona"]] = relationship(
        back_populates="document", order_by="Persona.id", cascade="all, delete-orphan"
    )


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    title: Mapped[str | None]

    document: Mapped[Document] = relationship(back_populates="sections")
    segments: Mapped[list["Segment"]] = relationship(back_populates="section", order_by="Segment.position")


class Segment(Base):
    """One sentence: the unit the director labels and the TTS renders."""

    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]  # reading order across the whole document
    block_index: Mapped[int]  # which block (paragraph, line of dialogue…) within the section
    block_kind: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)  # "" for a scene break (silence only)
    speaker: Mapped[str | None]  # from the parser
    block_direction: Mapped[str | None]  # e.g. "quietly"

    # The performance, filled in by the director
    role: Mapped[str] = mapped_column(default="NARRATOR")
    emotion: Mapped[str] = mapped_column(String(20), default="neutral")
    intensity: Mapped[int] = mapped_column(default=1)
    pace: Mapped[str] = mapped_column(String(10), default="normal")
    pause_before_ms: Mapped[int] = mapped_column(default=0)
    pause_after_ms: Mapped[int] = mapped_column(default=0)
    emphasis: Mapped[list[str]] = mapped_column(JSONB, default=list)

    document: Mapped[Document] = relationship(back_populates="segments")
    section: Mapped[Section] = relationship(back_populates="segments")


class Persona(Base):
    """A cast member and the voice that performs them."""

    __tablename__ = "personas"
    __table_args__ = (UniqueConstraint("document_id", "cast_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    cast_id: Mapped[str]  # NARRATOR or a speaker id such as KANG
    display_name: Mapped[str]
    gender: Mapped[str] = mapped_column(String(10))
    age: Mapped[str] = mapped_column(String(10))
    accent: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(Text)
    voice: Mapped[str] = mapped_column(String(30))
    speed: Mapped[float]

    document: Mapped[Document] = relationship(back_populates="personas")


class RenderJob(Base):
    """One run of the renderer over a document. Progress is counted in lines."""

    __tablename__ = "render_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued → rendering → done | failed | cancelled
    total_lines: Mapped[int] = mapped_column(default=0)
    done_lines: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None]


class ChapterAudio(Base):
    """The rendered audio of one section. Files live under settings.data_dir."""

    __tablename__ = "chapter_audio"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending → rendering → ready
    fingerprint: Mapped[str | None] = mapped_column(String(32))  # what the audio was rendered from
    duration_s: Mapped[float | None]

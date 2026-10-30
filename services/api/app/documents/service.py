import logging
import uuid
from dataclasses import asdict

from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.director.casting import auto_cast
from app.director.director import NARRATOR, Line, direct_document, direct_lines
from app.llm import LLM, LLMError
from app.models import ChapterAudio, Document, Persona, RenderJob, Section, Segment
from app.structure.models import ParsedDocument

log = logging.getLogger(__name__)


def init_db() -> None:
    """Create tables, and fail any run a server restart interrupted.

    Background tasks die with the process (e.g. on every `--reload`), so a document
    could otherwise stay "directing" forever.
    """
    try:
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            db.execute(
                update(Document)
                .where(Document.status == "directing")
                .values(status="failed", error="Interrupted by a server restart. Run the director again.")
            )
            db.execute(
                update(RenderJob)
                .where(RenderJob.status.in_(("queued", "rendering")))
                .values(status="failed", error="Interrupted by a server restart. Render again to continue.")
            )
            db.execute(update(ChapterAudio).where(ChapterAudio.status == "rendering").values(status="pending"))
            db.commit()
    except OperationalError:
        log.warning("Database unavailable at startup; /health will report it")


def create_document(db: Session, parsed: ParsedDocument) -> Document:
    document = Document(title=parsed.title, format=parsed.format, stats=parsed.stats.model_dump())
    position = 0
    for section_position, parsed_section in enumerate(parsed.sections):
        section = Section(position=section_position, title=parsed_section.title)
        document.sections.append(section)
        for block_index, block in enumerate(parsed_section.blocks):
            # A scene break has no sentences but still needs a (silent) place in the timeline
            for sentence in block.sentences or [""]:
                Segment(
                    document=document,
                    section=section,
                    position=position,
                    block_index=block_index,
                    block_kind=block.kind,
                    text=sentence,
                    speaker=block.speaker,
                    block_direction=block.direction,
                    role=block.speaker or NARRATOR,
                )
                position += 1
    db.add(document)
    db.commit()
    return document


def _lines(document: Document) -> list[Line]:
    return [
        Line(s.position, s.block_kind, s.text, s.speaker, s.block_direction) for s in document.segments
    ]


def _direct(db: Session, document: Document, llm: LLM) -> None:
    lines = _lines(document)
    direction = direct_document(
        llm,
        title=document.title,
        format=document.format,
        speakers=document.stats.get("speakers", []),
        lines=lines,
    )
    performances = {p.index: p for p in direct_lines(llm, direction, lines)}

    document.genre = direction.genre
    document.subgenre = direction.subgenre
    document.summary = direction.summary
    document.narrator_style = direction.narrator_style

    document.personas.clear()
    db.flush()  # delete old personas before inserting new ones (unique cast ids)
    document.personas.extend(Persona(**asdict(plan)) for plan in auto_cast(direction))

    for segment in document.segments:
        performance = performances[segment.position]
        segment.role = performance.role
        segment.emotion = performance.emotion
        segment.intensity = performance.intensity
        segment.pace = performance.pace
        segment.pause_before_ms = performance.pause_before_ms
        segment.pause_after_ms = performance.pause_after_ms
        segment.emphasis = performance.emphasis

    skipped = sum(1 for p in performances.values() if not p.labelled)
    document.warning = (
        f"{skipped} of {len(performances)} lines kept the default delivery (the AI skipped them)."
        if skipped
        else None
    )


def run_direction(document_id: uuid.UUID, llm: LLM) -> None:
    """Background task: direct a document. Never leaves it stuck in "directing"."""
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is None:
            return
        try:
            _direct(db, document, llm)
            document.status = "directed"
        except Exception as error:
            log.exception("Directing %s failed", document_id)
            db.rollback()
            document = db.get(Document, document_id)
            document.status = "failed"
            document.error = (
                str(error) if isinstance(error, LLMError) else "Something went wrong while directing. Please try again."
            )
        db.commit()

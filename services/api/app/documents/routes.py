"""Save a parsed document, run the AI director on it, and read the result.

Flow for the UI: POST /ingest/* (preview) → POST /documents (save)
→ POST /documents/{id}/direct (starts in the background) → poll GET /documents/{id}.
"""

import uuid
from collections.abc import Callable

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.documents.schemas import (
    DocumentDetail,
    DocumentSummary,
    DocumentUpdate,
    PersonaOut,
    PersonaUpdate,
    SegmentOut,
    SegmentUpdate,
)
from app.documents.service import create_document, run_direction
from app.llm import LLM, LLMError, make_llm
from app.models import Document, Segment
from app.structure.models import ParsedDocument
from app.tts.kokoro_voices import VOICES_BY_ID

router = APIRouter(prefix="/documents", tags=["documents"])


def get_llm_factory() -> Callable[[str | None], LLM]:
    """Overridden in tests with a fake LLM."""
    return make_llm


def _get(db: Session, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


def _get_editable(db: Session, document_id: uuid.UUID) -> Document:
    """Edits would race the director's background write, so they wait for it."""
    document = _get(db, document_id)
    if document.status == "directing":
        raise HTTPException(status_code=409, detail="Wait for the director to finish before editing.")
    return document


@router.post("", status_code=201, response_model=DocumentSummary)
def create(parsed: ParsedDocument, db: Session = Depends(get_db)):
    if parsed.stats.words == 0:
        raise HTTPException(status_code=422, detail="No readable text to save.")
    return create_document(db, parsed)


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)):
    return db.scalars(select(Document).order_by(Document.created_at.desc())).all()


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get(db, document_id)


@router.patch("/{document_id}", response_model=DocumentSummary)
def update_document(document_id: uuid.UUID, body: DocumentUpdate, db: Session = Depends(get_db)):
    document = _get_editable(db, document_id)
    document.title = body.title.strip()
    db.commit()
    return document


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    db.delete(_get_editable(db, document_id))
    db.commit()


@router.patch("/{document_id}/personas/{cast_id}", response_model=PersonaOut)
def update_persona(document_id: uuid.UUID, cast_id: str, body: PersonaUpdate, db: Session = Depends(get_db)):
    document = _get_editable(db, document_id)
    persona = next((p for p in document.personas if p.cast_id == cast_id), None)
    if persona is None:
        raise HTTPException(status_code=404, detail="No such cast member.")
    if body.voice is not None and body.voice not in VOICES_BY_ID:
        raise HTTPException(status_code=422, detail=f"Unknown voice: {body.voice}")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(persona, field, value)
    db.commit()
    return persona


@router.patch("/{document_id}/segments/{segment_id}", response_model=SegmentOut)
def update_segment(document_id: uuid.UUID, segment_id: int, body: SegmentUpdate, db: Session = Depends(get_db)):
    document = _get_editable(db, document_id)
    segment = db.get(Segment, segment_id)
    if segment is None or segment.document_id != document.id:
        raise HTTPException(status_code=404, detail="No such line.")
    if body.role is not None and body.role not in {p.cast_id for p in document.personas}:
        raise HTTPException(status_code=422, detail=f"{body.role} isn't in the cast.")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(segment, field, value)
    db.commit()
    return segment


@router.post("/{document_id}/direct", status_code=202, response_model=DocumentSummary)
def direct(
    document_id: uuid.UUID,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    llm_factory: Callable[[str | None], LLM] = Depends(get_llm_factory),
    x_llm_key: str | None = Header(default=None),  # bring-your-own-key, overrides the server's
):
    document = _get(db, document_id)
    if document.status == "directing":
        raise HTTPException(status_code=409, detail="The director is already working on this document.")
    try:
        llm = llm_factory(x_llm_key)
    except LLMError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    document.status = "directing"
    document.error = None
    db.commit()
    background.add_task(run_direction, document.id, llm)
    return document

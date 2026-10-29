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
from app.documents.schemas import DocumentDetail, DocumentSummary
from app.documents.service import create_document, run_direction
from app.llm import LLM, LLMError, make_llm
from app.models import Document
from app.structure.models import ParsedDocument

router = APIRouter(prefix="/documents", tags=["documents"])


def get_llm_factory() -> Callable[[str | None], LLM]:
    """Overridden in tests with a fake LLM."""
    return make_llm


def _get(db: Session, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
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

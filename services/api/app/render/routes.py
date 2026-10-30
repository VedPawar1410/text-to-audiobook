"""Start, watch and cancel rendering; serve chapter audio and manifests."""

import threading
import uuid
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChapterAudio, Document, Section
from app.render.export import FORMATS, NotReady, download_name, export_audiobook
from app.render.performance import fingerprint
from app.render.service import (
    active_job,
    chapter_files,
    chapter_plans,
    latest_job,
    render_job,
    request_cancel,
    start_job,
)
from app.tts import get_engine

router = APIRouter(prefix="/documents/{document_id}", tags=["render"])


class JobOut(BaseModel):
    id: int
    status: str  # queued | rendering | done | failed | cancelled
    total_lines: int
    done_lines: int
    error: str | None


class ChapterOut(BaseModel):
    section_id: int
    position: int
    title: str | None
    status: str  # pending | rendering | ready
    duration_s: float | None
    stale: bool  # ready, but edits since then change how it should sound
    version: str | None  # changes on re-render; lets the browser cache safely


class RenderStatus(BaseModel):
    job: JobOut | None
    chapters: list[ChapterOut]


def get_job_runner() -> Callable[[int], None]:
    """Start a render in a daemon thread. Tests override this to run inline."""

    def run(job_id: int) -> None:
        threading.Thread(target=render_job, args=(job_id, get_engine()), daemon=True, name=f"render-{job_id}").start()

    return run


def _document(db: Session, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


def _status(db: Session, document: Document) -> RenderStatus:
    job = latest_job(db, document.id)
    stored = {c.section_id: c for c in db.scalars(select(ChapterAudio).where(ChapterAudio.document_id == document.id))}
    chapters = []
    for section, steps in chapter_plans(document):
        chapter = stored.get(section.id)
        ready = chapter is not None and chapter.status == "ready"
        chapters.append(
            ChapterOut(
                section_id=section.id,
                position=section.position,
                title=section.title,
                status=chapter.status if chapter else "pending",
                duration_s=chapter.duration_s if ready else None,
                stale=ready and chapter.fingerprint != fingerprint(steps),
                version=chapter.fingerprint if ready else None,
            )
        )
    return RenderStatus(job=JobOut.model_validate(job, from_attributes=True) if job else None, chapters=chapters)


@router.get("/render", response_model=RenderStatus)
def render_status(document_id: uuid.UUID, db: Session = Depends(get_db)):
    return _status(db, _document(db, document_id))


@router.post("/render", status_code=202, response_model=RenderStatus)
def start_render(
    document_id: uuid.UUID, db: Session = Depends(get_db), run: Callable[[int], None] = Depends(get_job_runner)
):
    document = _document(db, document_id)
    if document.status != "directed":
        raise HTTPException(status_code=409, detail="Direct the document before rendering it.")
    if active_job(db, document.id):
        raise HTTPException(status_code=409, detail="This document is already rendering.")
    job = start_job(db, document)
    run(job.id)
    db.expire_all()  # an inline runner (tests) may have finished already
    return _status(db, document)


@router.post("/render/cancel", status_code=202)
def cancel_render(document_id: uuid.UUID, db: Session = Depends(get_db)):
    job = active_job(db, _document(db, document_id).id)
    if job is None:
        raise HTTPException(status_code=409, detail="Nothing is rendering.")
    request_cancel(job.id)
    return {"status": "cancelling"}


def _chapter_file(db: Session, document_id: uuid.UUID, section_id: int, index: int):
    section = db.get(Section, section_id)
    chapter = db.scalar(select(ChapterAudio).where(ChapterAudio.section_id == section_id))
    if section is None or section.document_id != document_id or chapter is None or chapter.status != "ready":
        raise HTTPException(status_code=404, detail="This chapter hasn't been rendered yet.")
    return chapter_files(document_id, section)[index]


@router.get("/chapters/{section_id}/audio")
def chapter_audio(document_id: uuid.UUID, section_id: int, db: Session = Depends(get_db)):
    # FileResponse answers Range requests, so players can seek without downloading everything
    return FileResponse(_chapter_file(db, document_id, section_id, 0), media_type="audio/mpeg")


@router.get("/chapters/{section_id}/manifest")
def chapter_manifest(document_id: uuid.UUID, section_id: int, db: Session = Depends(get_db)):
    return FileResponse(_chapter_file(db, document_id, section_id, 1), media_type="application/json")


class ExportOut(BaseModel):
    filename: str
    size_bytes: int


ExportFormat = Literal["m4b", "mp3"]


def _export(db: Session, document_id: uuid.UUID, extension: str):
    document = _document(db, document_id)
    try:
        return document, export_audiobook(db, document, extension)
    except NotReady:
        raise HTTPException(status_code=409, detail="Render every chapter before downloading the audiobook.") from None
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail="Couldn't package the audiobook. Please try again.") from error


@router.post("/exports/{extension}", response_model=ExportOut)
def prepare_export(document_id: uuid.UUID, extension: ExportFormat, db: Session = Depends(get_db)):
    """Build the file (an M4B of a long book takes a while) so the UI can show progress."""
    document, path = _export(db, document_id, extension)
    return ExportOut(filename=download_name(document, extension), size_bytes=path.stat().st_size)


@router.get("/exports/{extension}")
def download_export(document_id: uuid.UUID, extension: ExportFormat, db: Session = Depends(get_db)):
    document, path = _export(db, document_id, extension)  # instant once prepared
    # filename= makes it a download (Content-Disposition: attachment), not a page to play
    return FileResponse(path, media_type=FORMATS[extension].media_type, filename=download_name(document, extension))

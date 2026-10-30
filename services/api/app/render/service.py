"""Render a directed document into chapter audio.

Runs in a daemon thread rather than FastAPI's BackgroundTasks: a full book takes
about an hour, and uvicorn's reload waits for background tasks (seen in PR 6).
A daemon thread doesn't block restarts; init_db marks interrupted jobs failed.
"""

import json
import logging
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import ChapterAudio, Document, RenderJob, Section
from app.render.assembly import Mp3Writer, assemble
from app.render.cache import ClipCache, atomic_write
from app.render.performance import Step, fingerprint, plan_chapter
from app.tts.base import TTSEngine

log = logging.getLogger(__name__)

ACTIVE_STATUSES = ("queued", "rendering")
_cancel_events: dict[int, threading.Event] = {}


class Cancelled(Exception):
    pass


def document_dir(document_id: uuid.UUID) -> Path:
    return settings.data_dir / "documents" / str(document_id)


def chapter_files(document_id: uuid.UUID, section: Section) -> tuple[Path, Path]:
    stem = document_dir(document_id) / f"chapter-{section.position:03d}"
    return stem.with_suffix(".mp3"), stem.with_suffix(".json")


def chapter_plans(document: Document) -> list[tuple[Section, list[Step]]]:
    voices = {p.cast_id: (p.voice, p.speed) for p in document.personas}
    return [(section, plan_chapter(section.segments, voices, document.format)) for section in document.sections]


def active_job(db: Session, document_id: uuid.UUID) -> RenderJob | None:
    return db.scalar(
        select(RenderJob).where(RenderJob.document_id == document_id, RenderJob.status.in_(ACTIVE_STATUSES))
    )


def latest_job(db: Session, document_id: uuid.UUID) -> RenderJob | None:
    return db.scalar(select(RenderJob).where(RenderJob.document_id == document_id).order_by(RenderJob.id.desc()))


def start_job(db: Session, document: Document) -> RenderJob:
    job = RenderJob(document_id=document.id)
    db.add(job)
    db.commit()
    _cancel_events[job.id] = threading.Event()
    return job


def request_cancel(job_id: int) -> None:
    if event := _cancel_events.get(job_id):
        event.set()


def _lines(steps: list[Step]) -> int:
    return sum(1 for step in steps if step.speech)


def _render(db: Session, job: RenderJob, engine: TTSEngine, cancel: threading.Event) -> None:
    document = db.get(Document, job.document_id)
    plans = chapter_plans(document)
    job.status = "rendering"
    job.total_lines = sum(_lines(steps) for _, steps in plans)
    job.done_lines = 0
    db.commit()

    cache = ClipCache(settings.data_dir / "clips", engine)
    document_dir(document.id).mkdir(parents=True, exist_ok=True)
    chapters = {c.section_id: c for c in db.scalars(select(ChapterAudio).where(ChapterAudio.document_id == document.id))}
    last_commit = time.monotonic()

    def get_clip(text: str, voice: str, speed: float):
        nonlocal last_commit
        if cancel.is_set():
            raise Cancelled
        clip = cache.get(text, voice, speed)
        job.done_lines += 1
        if time.monotonic() - last_commit > 1:  # progress for the UI, about once a second
            db.commit()
            last_commit = time.monotonic()
        return clip

    for section, steps in plans:
        if cancel.is_set():  # also between chapters: some (scene breaks only) never fetch a clip
            raise Cancelled
        audio_path, manifest_path = chapter_files(document.id, section)
        chapter = chapters.get(section.id) or ChapterAudio(document_id=document.id, section_id=section.id)
        db.add(chapter)
        current = fingerprint(steps)

        if chapter.status == "ready" and chapter.fingerprint == current and audio_path.exists():
            job.done_lines += _lines(steps)  # already up to date: nothing to do
            continue

        chapter.status = "rendering"
        db.commit()
        with Mp3Writer(audio_path) as writer:
            manifest = assemble(steps, get_clip, writer.write)
        atomic_write(manifest_path, lambda p: p.write_text(json.dumps(manifest)))

        chapter.status = "ready"
        chapter.fingerprint = current
        chapter.duration_s = manifest["duration"]
        db.commit()

    log.info("Render %s done: %d clips rendered, %d from cache", job.id, cache.misses, cache.hits)


def render_job(job_id: int, engine: TTSEngine) -> None:
    """The job itself. Never leaves the job or a chapter stuck in "rendering"."""
    cancel = _cancel_events.setdefault(job_id, threading.Event())
    with SessionLocal() as db:
        job = db.get(RenderJob, job_id)
        try:
            _render(db, job, engine, cancel)
            job.status = "done"
        except Exception as error:
            if not isinstance(error, Cancelled):
                log.exception("Render %s failed", job_id)
            db.rollback()
            job = db.get(RenderJob, job_id)
            job.status = "cancelled" if isinstance(error, Cancelled) else "failed"
            job.error = None if isinstance(error, Cancelled) else f"Rendering failed: {str(error)[:300]}"
            db.execute(
                update(ChapterAudio)
                .where(ChapterAudio.document_id == job.document_id, ChapterAudio.status == "rendering")
                .values(status="pending")
            )
        job.finished_at = datetime.now(UTC)
        db.commit()
    _cancel_events.pop(job_id, None)

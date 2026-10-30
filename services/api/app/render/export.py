"""Package the chapter MP3s as one download with chapter markers: an M4B for
audiobook apps, or a single MP3 that plays anywhere.

The chapters are already encoded, so this joins rather than renders:
- MP3 is a stream copy, about a second for a long book
- M4B re-encodes to AAC, which audiobook apps expect: ~14 s per hour of audio (measured in PR 10)
Results are cached under a key of everything that ends up in the file.
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChapterAudio, Document, Section
from app.render.service import chapter_files, document_dir


@dataclass(frozen=True)
class Format:
    media_type: str
    codec: list[str]
    copied: bool  # chapters' frames go in as they are, encoder padding included


FORMATS = {
    "m4b": Format("audio/mp4", ["-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", "-f", "ipod"], copied=False),
    "mp3": Format("audio/mpeg", ["-c", "copy", "-id3v2_version", "3", "-f", "mp3"], copied=True),
}

# One export at a time: a second request for the same file waits, then finds it cached
_lock = threading.Lock()


class NotReady(Exception):
    pass


def chapter_title(section: Section) -> str:
    return section.title or ("Opening" if section.position == 0 else f"Part {section.position + 1}")


def download_name(document: Document, extension: str) -> str:
    title = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", document.title or "").strip() or "Audiobook"
    return f"{title}.{extension}"


def _escape(value: str) -> str:
    # ffmetadata treats these as syntax unless backslash-escaped
    return re.sub(r"([=;#\\\n])", r"\\\1", value)


def metadata(document: Document, chapters: list[tuple[str, float]]) -> str:
    """An ffmetadata file: the book's tags, then each chapter's span in milliseconds."""
    title = _escape(document.title or "Audiobook")
    lines = [";FFMETADATA1", f"title={title}", f"album={title}", "artist=Narrate"]
    if document.genre:
        lines.append(f"genre={_escape(document.genre)}")
    start = 0
    for name, duration in chapters:
        end = start + round(duration * 1000)
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={start}", f"END={end}", f"title={_escape(name)}"]
        start = end
    return "\n".join(lines) + "\n"


def _probe(path: Path, *entries: str) -> list[str]:
    output = subprocess.run(
        ["ffprobe", "-v", "error", *entries, "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True
    )
    return output.stdout.strip().split(",")


def probe_duration(path: Path, copied: bool) -> float:
    """How long a chapter lasts inside the joined file, so each marker lands on its chapter.

    Not the manifest's duration: MP3 pads every file to whole frames. Re-encoding decodes
    each chapter with that padding trimmed (ffprobe's duration); a stream copy keeps every
    frame, so count them (576 samples per frame below 32 kHz, 1152 above).
    """
    if not copied:
        return float(_probe(path, "-show_entries", "format=duration")[0])
    sample_rate, frames = _probe(
        path, "-select_streams", "a:0", "-count_packets", "-show_entries", "stream=sample_rate,nb_read_packets"
    )
    per_frame = 1152 if int(sample_rate) >= 32_000 else 576
    return int(frames) * per_frame / int(sample_rate)


def _chapters(db: Session, document: Document) -> list[tuple[Section, ChapterAudio, Path]]:
    stored = {c.section_id: c for c in db.scalars(select(ChapterAudio).where(ChapterAudio.document_id == document.id))}
    chapters = []
    for section in document.sections:
        chapter = stored.get(section.id)
        audio_path = chapter_files(document.id, section)[0]
        if chapter is None or chapter.status != "ready" or not audio_path.exists():
            raise NotReady
        chapters.append((section, chapter, audio_path))
    return chapters


def _playlist_line(path: Path) -> str:
    quoted = str(path).replace("'", "'\\''")  # the concat format's quoting
    return f"file '{quoted}'\n"


def export_audiobook(db: Session, document: Document, extension: str) -> Path:
    """The whole book as one file, built on first request and cached after that."""
    chapters = _chapters(db, document)
    if not chapters:
        raise NotReady
    recipe = [extension, document.title, document.genre, [(chapter_title(s), c.fingerprint) for s, c, _ in chapters]]
    key = hashlib.sha256(json.dumps(recipe).encode()).hexdigest()[:16]
    folder = document_dir(document.id) / "exports"
    target = folder / f"{key}.{extension}"

    with _lock:
        if target.exists():
            return target
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as work:
            playlist = Path(work) / "chapters.txt"
            playlist.write_text("".join(_playlist_line(path) for _, _, path in chapters))
            tags = Path(work) / "metadata.txt"
            tags.write_text(metadata(document, [(chapter_title(s), probe_duration(path, FORMATS[extension].copied)) for s, _, path in chapters]))
            built = Path(work) / f"book.{extension}"
            result = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(playlist),
                 "-i", str(tags), "-map", "0:a", "-map_metadata", "1", "-map_chapters", "1",
                 *FORMATS[extension].codec, str(built)],
                capture_output=True, text=True, check=False,
            )  # fmt: skip
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr[:300]}")
            os.replace(built, target)
        for old in folder.glob(f"*.{extension}"):  # earlier versions of this book
            if old != target:
                old.unlink(missing_ok=True)
    return target

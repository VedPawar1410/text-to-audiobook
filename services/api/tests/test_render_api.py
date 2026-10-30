import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import SessionLocal
from app.documents.routes import get_llm_factory
from app.documents.service import init_db
from app.main import app
from app.models import RenderJob
from app.render.routes import get_job_runner
from app.render.service import document_dir, render_job, request_cancel
from tests.fakes import FakeEngine, FakeLLM, cast_member, direction, label

client = TestClient(app)
SCREENPLAY = (Path(__file__).parent / "fixtures" / "citadel_screenplay.txt").read_text()


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    yield tmp_path
    app.dependency_overrides.clear()


@pytest.fixture
def engine():
    """Renders run inline with the fake engine, so tests see the finished result."""
    fake = FakeEngine()
    app.dependency_overrides[get_job_runner] = lambda: (lambda job_id: render_job(job_id, fake))
    return fake


def directed_screenplay() -> str:
    llm = FakeLLM(
        document=direction(cast=[cast_member("KANG"), cast_member("THOR")]),
        labeller=lambda i: label(i, emotion="ominous", intensity=2),
    )
    app.dependency_overrides[get_llm_factory] = lambda: (lambda key: llm)
    parsed = client.post("/ingest/text", json={"text": SCREENPLAY}).json()
    document_id = client.post("/documents", json=parsed).json()["id"]
    client.post(f"/documents/{document_id}/direct")
    return document_id


def test_render_produces_playable_chapters_with_manifests(engine):
    document_id = directed_screenplay()

    started = client.post(f"/documents/{document_id}/render")
    status = client.get(f"/documents/{document_id}/render").json()

    assert started.status_code == 202
    assert status["job"]["status"] == "done"
    assert status["job"]["done_lines"] == status["job"]["total_lines"] > 0
    assert all(c["status"] == "ready" and c["duration_s"] > 0 and not c["stale"] for c in status["chapters"])

    chapter = status["chapters"][1]  # the throne-room scene
    audio = client.get(f"/documents/{document_id}/chapters/{chapter['section_id']}/audio")
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/mpeg"

    manifest = client.get(f"/documents/{document_id}/chapters/{chapter['section_id']}/manifest").json()
    starts = [s["start"] for s in manifest["segments"]]
    assert starts == sorted(starts)
    assert manifest["segments"][0]["words"][0]["text"] == "Interior."  # the spoken scene heading


def test_chapter_audio_supports_seeking(engine):
    document_id = directed_screenplay()
    client.post(f"/documents/{document_id}/render")
    section_id = client.get(f"/documents/{document_id}/render").json()["chapters"][1]["section_id"]

    partial = client.get(f"/documents/{document_id}/chapters/{section_id}/audio", headers={"Range": "bytes=100-199"})

    assert partial.status_code == 206
    assert len(partial.content) == 100


def test_only_changed_lines_are_rendered_again(engine):
    document_id = directed_screenplay()
    client.post(f"/documents/{document_id}/render")
    first_render = len(engine.calls)

    client.patch(f"/documents/{document_id}/personas/KANG", json={"voice": "am_onyx"})
    stale = client.get(f"/documents/{document_id}/render").json()["chapters"]
    client.post(f"/documents/{document_id}/render")

    assert [c["stale"] for c in stale] == [False, True, False]  # Kang only speaks in scene 1
    rerendered = engine.calls[first_render:]
    kang_lines = 3  # "You came.", "They always come.", and his long line
    assert len(rerendered) == kang_lines + 1  # "Every timeline ends, Odinson." is two sentences
    assert all(voice == "am_onyx" for _, voice, _ in rerendered)


def test_rendering_again_without_changes_does_nothing(engine):
    document_id = directed_screenplay()
    client.post(f"/documents/{document_id}/render")
    calls = len(engine.calls)

    client.post(f"/documents/{document_id}/render")

    assert len(engine.calls) == calls
    assert client.get(f"/documents/{document_id}/render").json()["job"]["status"] == "done"


def test_a_cancelled_render_leaves_no_chapter_stuck(engine):
    document_id = directed_screenplay()

    def cancel_then_run(job_id):
        request_cancel(job_id)
        render_job(job_id, engine)

    app.dependency_overrides[get_job_runner] = lambda: cancel_then_run
    client.post(f"/documents/{document_id}/render")
    status = client.get(f"/documents/{document_id}/render").json()

    assert status["job"]["status"] == "cancelled"
    assert all(c["status"] == "pending" for c in status["chapters"])


def test_a_failed_render_reports_why():
    failing = FakeEngine(fail_on="Odinson")
    app.dependency_overrides[get_job_runner] = lambda: (lambda job_id: render_job(job_id, failing))
    document_id = directed_screenplay()

    client.post(f"/documents/{document_id}/render")
    status = client.get(f"/documents/{document_id}/render").json()

    assert status["job"]["status"] == "failed"
    assert "synthesis exploded" in status["job"]["error"]
    assert "rendering" not in {c["status"] for c in status["chapters"]}


def test_guards(engine):
    parsed = client.post("/ingest/text", json={"text": SCREENPLAY}).json()
    undirected = client.post("/documents", json=parsed).json()["id"]

    assert client.post(f"/documents/{undirected}/render").status_code == 409
    assert client.post(f"/documents/{undirected}/render/cancel").status_code == 409
    assert client.get(f"/documents/{undirected}/chapters/1/audio").status_code == 404


def test_rendering_blocks_redirecting_and_deleting(engine):
    document_id = directed_screenplay()
    with SessionLocal() as db:
        db.add(RenderJob(document_id=document_id, status="rendering"))
        db.commit()

    assert client.post(f"/documents/{document_id}/direct").status_code == 409
    assert client.delete(f"/documents/{document_id}").status_code == 409
    assert client.post(f"/documents/{document_id}/render").status_code == 409


def test_deleting_a_document_removes_its_audio(engine):
    document_id = directed_screenplay()
    client.post(f"/documents/{document_id}/render")
    assert document_dir(document_id).exists()

    client.delete(f"/documents/{document_id}")

    assert not document_dir(document_id).exists()


def test_renders_interrupted_by_a_restart_are_marked_failed(engine):
    document_id = directed_screenplay()
    with SessionLocal() as db:
        db.add(RenderJob(document_id=document_id, status="rendering"))
        db.commit()

    init_db()

    job = client.get(f"/documents/{document_id}/render").json()["job"]
    assert job["status"] == "failed" and "restart" in job["error"]


def probe(path: Path) -> dict:
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_chapters", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    return json.loads(output.stdout)


@pytest.mark.parametrize(("extension", "media_type"), [("m4b", "audio/mp4"), ("mp3", "audio/mpeg")])
def test_the_audiobook_downloads_as_one_file_with_chapters(engine, tmp_path, extension, media_type):
    document_id = directed_screenplay()
    client.post(f"/documents/{document_id}/render")
    chapters = client.get(f"/documents/{document_id}/render").json()["chapters"]

    prepared = client.post(f"/documents/{document_id}/exports/{extension}")
    download = client.get(f"/documents/{document_id}/exports/{extension}")

    assert prepared.status_code == 200
    assert prepared.json()["filename"] == f"THE CITADEL AT THE END OF TIME.{extension}"
    assert download.headers["content-type"] == media_type
    assert download.headers["content-disposition"].startswith("attachment;")
    assert len(download.content) == prepared.json()["size_bytes"]

    saved = tmp_path / f"book.{extension}"
    saved.write_bytes(download.content)
    info = probe(saved)
    marks = info["chapters"]
    assert [m["tags"]["title"] for m in marks] == ["Opening", "INT. CITADEL THRONE ROOM - NIGHT", "EXT. THE VOID - CONTINUOUS"]
    assert [m["tags"]["title"] for m in marks][1:] == [c["title"] for c in chapters][1:]
    assert float(marks[1]["start_time"]) == pytest.approx(float(marks[0]["end_time"]))  # back to back
    # The markers follow the real audio: the last one ends where the file does
    assert float(marks[-1]["end_time"]) == pytest.approx(float(info["format"]["duration"]), abs=0.1)
    assert info["format"]["tags"]["title"] == "THE CITADEL AT THE END OF TIME"


def test_exports_are_cached_until_something_in_them_changes(engine):
    document_id = directed_screenplay()
    client.post(f"/documents/{document_id}/render")
    exports = document_dir(document_id) / "exports"

    client.post(f"/documents/{document_id}/exports/mp3")
    first = next(exports.glob("*.mp3"))
    built_at = first.stat().st_mtime_ns
    client.post(f"/documents/{document_id}/exports/mp3")
    assert first.stat().st_mtime_ns == built_at  # the second request reused it

    client.patch(f"/documents/{document_id}", json={"title": "The Citadel"})
    renamed = client.post(f"/documents/{document_id}/exports/mp3").json()

    assert renamed["filename"] == "The Citadel.mp3"
    assert [p.name for p in exports.glob("*.mp3")] != [first.name]  # rebuilt, old copy removed
    assert len(list(exports.glob("*.mp3"))) == 1


def test_export_needs_every_chapter_recorded(engine):
    document_id = directed_screenplay()

    assert client.post(f"/documents/{document_id}/exports/m4b").status_code == 409
    assert client.get(f"/documents/{document_id}/exports/m4b").status_code == 409
    assert client.post(f"/documents/{document_id}/exports/wav").status_code == 422


def test_export_metadata_escapes_ffmetadata_syntax():
    from app.models import Document
    from app.render.export import metadata

    text = metadata(Document(title="Part=1; #2\\x", genre="sci-fi"), [("A=B", 1.5), ("C", 2.25)])

    assert "title=Part\\=1\\; \\#2\\\\x" in text
    assert "START=0\nEND=1500\ntitle=A\\=B" in text
    assert "START=1500\nEND=3750\ntitle=C" in text

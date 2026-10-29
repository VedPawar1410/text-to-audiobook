from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import llm as llm_module
from app.db import SessionLocal
from app.documents.routes import get_llm_factory
from app.documents.service import init_db
from app.main import app
from app.models import Document
from tests.fakes import FakeLLM, cast_member, direction, label

client = TestClient(app)
FAN_SCRIPT = (Path(__file__).parent / "fixtures" / "citadel_fan_script.txt").read_text()
CAST = [cast_member("KANG"), cast_member("THOR"), cast_member("STRANGE"), cast_member("WANDA", gender="female")]


def save_fan_script() -> str:
    parsed = client.post("/ingest/text", json={"text": FAN_SCRIPT}).json()
    response = client.post("/documents", json=parsed)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def fake_llm():
    llm = FakeLLM(document=direction(cast=CAST), labeller=lambda i: label(i, emotion="ominous", intensity=2))
    app.dependency_overrides[get_llm_factory] = lambda: (lambda key: llm)
    yield llm
    app.dependency_overrides.clear()


def test_saved_document_keeps_its_structure():
    document_id = save_fan_script()

    body = client.get(f"/documents/{document_id}").json()

    assert body["status"] == "parsed"
    assert [s["title"] for s in body["sections"]] == ["Scene 1 - The Citadel", "Scene 2 - The Void"]
    segments = [seg for s in body["sections"] for seg in s["segments"]]
    assert [seg["position"] for seg in segments] == list(range(len(segments)))
    assert segments[1]["role"] == "KANG" and segments[1]["text"] == "Every timeline ends."
    assert client.get("/documents").json()[0]["id"] == document_id


def test_directing_fills_genre_cast_and_performances(fake_llm):
    document_id = save_fan_script()

    started = client.post(f"/documents/{document_id}/direct")
    body = client.get(f"/documents/{document_id}").json()  # TestClient runs background tasks inline

    assert started.status_code == 202 and started.json()["status"] == "directing"
    assert body["status"] == "directed" and body["warning"] is None
    assert body["genre"] == "screenplay"
    assert [p["cast_id"] for p in body["personas"]] == ["NARRATOR", "KANG", "THOR", "STRANGE", "WANDA"]
    assert len({p["voice"] for p in body["personas"]}) == 5
    dialogue = [seg for s in body["sections"] for seg in s["segments"] if seg["block_kind"] == "dialogue"]
    assert all(seg["emotion"] == "ominous" and seg["intensity"] == 2 for seg in dialogue)


def test_directing_again_replaces_the_cast(fake_llm):
    document_id = save_fan_script()

    client.post(f"/documents/{document_id}/direct")
    client.post(f"/documents/{document_id}/direct")

    assert len(client.get(f"/documents/{document_id}").json()["personas"]) == 5


def test_llm_failure_marks_the_document_failed(fake_llm):
    fake_llm.fail_document = True
    document_id = save_fan_script()

    client.post(f"/documents/{document_id}/direct")
    body = client.get(f"/documents/{document_id}").json()

    assert body["status"] == "failed"
    assert "unavailable" in body["error"]


def test_directing_without_any_key_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "gemini_api_key", None)
    document_id = save_fan_script()

    response = client.post(f"/documents/{document_id}/direct")

    assert response.status_code == 400
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_unknown_document_is_404():
    assert client.get("/documents/00000000-0000-0000-0000-000000000000").status_code == 404


def test_runs_interrupted_by_a_restart_are_marked_failed():
    document_id = save_fan_script()
    with SessionLocal() as db:
        db.get(Document, document_id).status = "directing"
        db.commit()

    init_db()

    body = client.get(f"/documents/{document_id}").json()
    assert body["status"] == "failed" and "restart" in body["error"]

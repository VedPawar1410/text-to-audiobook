from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.documents.routes import get_llm_factory
from app.main import app
from app.models import Document
from tests.fakes import FakeLLM, cast_member, direction

client = TestClient(app)
FAN_SCRIPT = (Path(__file__).parent / "fixtures" / "citadel_fan_script.txt").read_text()


@pytest.fixture
def directed_id():
    """A fan script saved and directed by the fake LLM."""
    llm = FakeLLM(document=direction(cast=[cast_member(s) for s in ("KANG", "THOR", "STRANGE", "WANDA")]))
    app.dependency_overrides[get_llm_factory] = lambda: (lambda key: llm)
    parsed = client.post("/ingest/text", json={"text": FAN_SCRIPT}).json()
    document_id = client.post("/documents", json=parsed).json()["id"]
    client.post(f"/documents/{document_id}/direct")
    yield document_id
    app.dependency_overrides.clear()


def segments(document_id):
    body = client.get(f"/documents/{document_id}").json()
    return [seg for s in body["sections"] for seg in s["segments"]]


def test_rename_document(directed_id):
    response = client.patch(f"/documents/{directed_id}", json={"title": "  The Kang Dynasty  "})

    assert response.status_code == 200
    assert client.get(f"/documents/{directed_id}").json()["title"] == "The Kang Dynasty"
    assert client.patch(f"/documents/{directed_id}", json={"title": ""}).status_code == 422


def test_recast_a_persona(directed_id):
    response = client.patch(f"/documents/{directed_id}/personas/KANG", json={"voice": "am_onyx", "speed": 0.9})

    assert response.status_code == 200
    kang = next(p for p in client.get(f"/documents/{directed_id}").json()["personas"] if p["cast_id"] == "KANG")
    assert (kang["voice"], kang["speed"]) == ("am_onyx", 0.9)
    assert kang["display_name"] == "Kang"  # fields not sent are left alone


def test_recast_rejects_unknown_voices_and_cast_members(directed_id):
    assert client.patch(f"/documents/{directed_id}/personas/KANG", json={"voice": "xx_nobody"}).status_code == 422
    assert client.patch(f"/documents/{directed_id}/personas/NOBODY", json={"speed": 1}).status_code == 404
    assert client.patch(f"/documents/{directed_id}/personas/KANG", json={"speed": 5}).status_code == 422


def test_override_a_line(directed_id):
    line = segments(directed_id)[1]

    response = client.patch(
        f"/documents/{directed_id}/segments/{line['id']}", json={"emotion": "whispering", "intensity": 3}
    )

    assert response.status_code == 200
    updated = segments(directed_id)[1]
    assert (updated["emotion"], updated["intensity"], updated["role"]) == ("whispering", 3, line["role"])


def test_line_overrides_are_validated(directed_id):
    line_id = segments(directed_id)[1]["id"]

    assert client.patch(f"/documents/{directed_id}/segments/{line_id}", json={"emotion": "giddy"}).status_code == 422
    assert client.patch(f"/documents/{directed_id}/segments/{line_id}", json={"role": "LOKI"}).status_code == 422
    assert client.patch(f"/documents/{directed_id}/segments/999999", json={"intensity": 2}).status_code == 404


def test_edits_wait_for_the_director(directed_id):
    with SessionLocal() as db:
        db.get(Document, directed_id).status = "directing"
        db.commit()

    assert client.patch(f"/documents/{directed_id}", json={"title": "x"}).status_code == 409
    assert client.patch(f"/documents/{directed_id}/personas/KANG", json={"speed": 1}).status_code == 409


def test_delete_document(directed_id):
    assert client.delete(f"/documents/{directed_id}").status_code == 204
    assert client.get(f"/documents/{directed_id}").status_code == 404
    assert client.get("/documents").json() == []

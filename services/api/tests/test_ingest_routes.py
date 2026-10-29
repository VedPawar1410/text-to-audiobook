from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.pdf_factory import make_pdf, page_of_lines

client = TestClient(app)
FIXTURES = Path(__file__).parent / "fixtures"


def test_ingest_pasted_text():
    text = (FIXTURES / "citadel_fan_script.txt").read_text()

    response = client.post("/ingest/text", json={"text": text})

    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "screenplay"
    assert body["stats"]["speakers"] == ["KANG", "THOR", "STRANGE", "WANDA"]


def test_ingest_rejects_text_with_no_words():
    assert client.post("/ingest/text", json={"text": "* * *"}).status_code == 422
    assert client.post("/ingest/text", json={"text": ""}).status_code == 422


def test_ingest_markdown_file_uses_heading_as_title():
    data = (FIXTURES / "last_timeline.md").read_bytes()

    response = client.post("/ingest/file", files={"file": ("story.md", data, "text/markdown")})

    assert response.status_code == 200
    assert response.json()["title"] == "The Last Timeline"


def test_ingest_text_file_falls_back_to_file_name_as_title():
    response = client.post("/ingest/file", files={"file": ("my_notes.txt", b"Just one line.", "text/plain")})

    assert response.json()["title"] == "my_notes"


def test_ingest_pdf_file():
    pdf = make_pdf([page_of_lines(["Chapter One", "", "The hall was silent."])])

    response = client.post("/ingest/file", files={"file": ("book.pdf", pdf, "application/pdf")})

    assert response.status_code == 200
    assert response.json()["sections"][0]["title"] == "Chapter One"


def test_ingest_rejects_unsupported_and_broken_files():
    docx = client.post("/ingest/file", files={"file": ("a.docx", b"PK..", "application/octet-stream")})
    broken = client.post("/ingest/file", files={"file": ("a.pdf", b"nope", "application/pdf")})

    assert docx.status_code == 415
    assert broken.status_code == 422


def test_ingest_url_refuses_local_addresses():
    response = client.post("/ingest/url", json={"url": "http://localhost:8000/health"})

    assert response.status_code == 422
    assert "private or local" in response.json()["detail"]

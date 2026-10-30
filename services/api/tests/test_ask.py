from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import llm as llm_module
from app.documents.routes import get_llm_factory
from app.main import app
from tests.fakes import FakeLLM, cast_member, direction

client = TestClient(app)
SCREENPLAY = (Path(__file__).parent / "fixtures" / "citadel_screenplay.txt").read_text()


@pytest.fixture
def fake():
    llm = FakeLLM(document=direction(cast=[cast_member("KANG"), cast_member("THOR")]))
    app.dependency_overrides[get_llm_factory] = lambda: (lambda key: llm)
    parsed = client.post("/ingest/text", json={"text": SCREENPLAY}).json()
    document_id = client.post("/documents", json=parsed).json()["id"]
    client.post(f"/documents/{document_id}/direct")
    yield llm, document_id
    app.dependency_overrides.clear()


def segment_id(document_id: str, text: str) -> int:
    body = client.get(f"/documents/{document_id}").json()
    return next(g["id"] for s in body["sections"] for g in s["segments"] if g["text"] == text)


def test_the_answer_streams_back(fake):
    llm, document_id = fake

    response = client.post(f"/documents/{document_id}/ask", json={"question": "Why is Kang so calm?"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text.strip() == llm.answer


def test_the_prompt_grounds_the_question_in_the_reading(fake):
    llm, document_id = fake
    line = segment_id(document_id, "You came.")

    client.post(
        f"/documents/{document_id}/ask",
        json={
            "question": "What does he mean?",
            "selection": "They always come.",
            "segment_id": line,
            "history": [{"role": "user", "text": "Who is Kang?"}, {"role": "assistant", "text": "A conqueror."}],
        },
    )

    prompt = llm.prompts[-1]
    assert "A conqueror waits at the end of time." in prompt  # the director's summary
    assert "Kang: You came." in prompt  # nearby dialogue, labelled by character
    assert "Thor: Where are the others?" in prompt
    assert 'selected this passage: "They always come."' in prompt
    assert "Reader: Who is Kang?" in prompt and "You: A conqueror." in prompt
    assert prompt.rstrip().endswith("The reader asks: What does he mean?")


def test_without_a_position_the_prompt_says_so(fake):
    llm, document_id = fake

    client.post(f"/documents/{document_id}/ask", json={"question": "What is this?"})

    assert "position is unknown" in llm.prompts[-1]


def test_a_failure_becomes_part_of_the_answer(fake):
    llm, document_id = fake
    llm.fail_document = True

    response = client.post(f"/documents/{document_id}/ask", json={"question": "Hello?"})

    assert response.status_code == 200  # streaming had already begun
    assert "unavailable" in response.text


def test_validation(fake):
    _, document_id = fake
    too_long_history = [{"role": "user", "text": "x"}] * 13

    assert client.post(f"/documents/{document_id}/ask", json={"question": ""}).status_code == 422
    assert client.post(f"/documents/{document_id}/ask", json={"question": "q", "history": too_long_history}).status_code == 422
    assert client.post("/documents/00000000-0000-0000-0000-000000000000/ask", json={"question": "q"}).status_code == 404


def test_asking_without_a_key_is_a_clear_error(fake, monkeypatch):
    _, document_id = fake
    app.dependency_overrides.clear()
    monkeypatch.setattr(llm_module.settings, "gemini_api_key", None)

    response = client.post(f"/documents/{document_id}/ask", json={"question": "Hello?"})

    assert response.status_code == 400
    assert "GEMINI_API_KEY" in response.json()["detail"]

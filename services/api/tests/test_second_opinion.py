"""The optional AI second opinion (step 6 of the revive). The provider is faked: no network."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.structure import parse_text
from app.structure import second_opinion as module
from app.structure.second_opinion import doubtful_blocks, second_opinion

LONG = "The harbour was quiet that night, and nobody on the quay said a word about the ship. " * 2
THREAD = f"My Thread\n\nThe harbour\n{LONG}\nShow more\n{LONG}\nNight crossing\n{LONG}"


def _fake(answer: str, calls: list | None = None):
    def ask(payload: str) -> str:
        if calls is not None:
            calls.append(payload)
        return answer

    return ask


def _blocks(document):
    return [(b.kind, b.text) for s in document.sections for b in s.blocks]


def test_off_by_default_means_no_call_and_no_change(monkeypatch):
    calls: list = []
    monkeypatch.setattr(module, "_ask_claude", _fake("1 H", calls))
    document = parse_text(THREAD)
    assert second_opinion(document) is document  # settings.structure_ai is "off"
    assert calls == []


def test_only_short_standalone_non_sentences_are_doubtful():
    document = parse_text(THREAD)
    texts = [document.sections[s].blocks[b].text for s, b in doubtful_blocks(document)]
    assert texts == ["The harbour", "Show more", "Night crossing"]


def test_the_models_labels_are_applied_and_listed(monkeypatch):
    calls: list = []
    monkeypatch.setattr(module, "_ask_claude", _fake("1 H\n2 X\n3 H", calls))

    revised = second_opinion(parse_text(THREAD), provider="claude")

    assert [s.title for s in revised.sections] == ["The harbour", "Night crossing"]
    assert ("paragraph", "Show more") not in _blocks(revised)
    assert "1. ..." in calls[0] and "|| Show more ||" in calls[0]  # numbered, with context on both sides
    assert '"Show more" → skipped' in revised.notes[-1]
    assert revised.title == "My Thread"


def test_long_lines_can_never_be_deleted_and_stray_answers_are_ignored(monkeypatch):
    monkeypatch.setattr(module, "_ask_claude", _fake("1 X\n2 X\n3 X\n4 X\n99 X\nnonsense"))
    revised = second_opinion(parse_text(THREAD), provider="claude")
    assert [text for kind, text in _blocks(revised)] == [LONG.strip()] * 3  # only the 3 short lines went


def test_a_provider_failure_keeps_the_rules_result(monkeypatch):
    def broken(payload: str) -> str:
        raise RuntimeError("overloaded")

    monkeypatch.setattr(module, "_ask_claude", broken)
    document = parse_text(THREAD)
    before = _blocks(document)
    result = second_opinion(document, provider="claude")
    assert _blocks(result) == before
    assert "unavailable" in result.notes[-1]


def test_screenplays_are_left_alone(monkeypatch):
    calls: list = []
    monkeypatch.setattr(module, "_ask_claude", _fake("1 H", calls))
    script = "INT. CITADEL - NIGHT\n\nA vast hall.\n\nKANG\nEvery timeline ends.\n\nEXT. VOID - CONTINUOUS\n\nNothing."
    document = parse_text(script)
    assert document.format == "screenplay"
    assert second_opinion(document, provider="claude") is document and calls == []


def test_import_uses_it_when_switched_on(monkeypatch):
    monkeypatch.setattr(settings, "structure_ai", "claude")
    monkeypatch.setattr(module, "_ask_claude", _fake("1 H\n2 X\n3 H"))

    response = TestClient(app).post("/ingest/text", json={"text": THREAD})

    assert response.status_code == 200
    assert [s["title"] for s in response.json()["sections"]] == ["The harbour", "Night crossing"]
    assert response.json()["notes"]

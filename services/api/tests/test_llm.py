from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors
from pydantic import BaseModel

from app import llm as llm_module
from app.llm import GeminiLLM, LLMError, make_llm


class Answer(BaseModel):
    word: str


OK = '{"word": "ok"}'


def api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"code": code, "message": "x", "status": "S"}})


def gemini(outcomes, models=("first", "second")):
    """A GeminiLLM whose client replays `outcomes` (text or exceptions) in order."""
    calls: list[str] = []
    queue = list(outcomes)

    def generate_content(*, model, contents, config):
        calls.append(model)
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    return GeminiLLM("key", list(models), backoff_seconds=0, client=client), calls


def ask(llm):
    return llm.generate_json(system="s", prompt="p", schema=Answer)


def test_overloaded_model_is_retried():
    llm, calls = gemini([api_error(503), api_error(429), OK])

    assert ask(llm).word == "ok"
    assert calls == ["first", "first", "first"]


def test_retired_model_falls_through_to_the_next():
    llm, calls = gemini([api_error(404), OK])

    assert ask(llm).word == "ok"
    assert calls == ["first", "second"]


def test_timeouts_and_dropped_connections_are_retried():
    llm, calls = gemini([httpx.ReadTimeout("slow"), httpx.ConnectError("dropped"), OK])

    assert ask(llm).word == "ok"
    assert len(calls) == 3


def test_invalid_json_is_asked_again():
    llm, calls = gemini(["not json", '{"other": 1}', OK])

    assert ask(llm).word == "ok"
    assert len(calls) == 3


def test_rejected_key_fails_immediately():
    llm, calls = gemini([api_error(401)])

    with pytest.raises(LLMError, match="key was rejected"):
        ask(llm)
    assert calls == ["first"]


def test_bad_request_is_not_retried():
    llm, calls = gemini([api_error(400)])

    with pytest.raises(LLMError, match="400"):
        ask(llm)
    assert calls == ["first"]


def test_gives_up_after_every_model_and_attempt():
    llm, calls = gemini([api_error(503)] * 6)

    with pytest.raises(LLMError, match="unavailable"):
        ask(llm)
    assert calls == ["first"] * 3 + ["second"] * 3


def test_make_llm_needs_a_key(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "gemini_api_key", None)

    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        make_llm()
    assert make_llm("request-key") is not None  # a per-request key is enough

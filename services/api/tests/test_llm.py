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


def streaming(outcomes, models=("first", "second")):
    """A GeminiLLM whose streaming client replays outcomes: an exception, or a list of chunks
    (which may itself contain an exception, raised mid-stream)."""
    calls: list[str] = []
    queue = list(outcomes)

    def generate_content_stream(*, model, contents, config):
        calls.append(model)
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome

        def chunks():
            for item in outcome:
                if isinstance(item, Exception):
                    raise item
                yield SimpleNamespace(text=item)

        return chunks()

    client = SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate_content_stream))
    return GeminiLLM("key", list(models), backoff_seconds=0, client=client), calls


def stream(llm):
    return llm.stream_text(system="s", prompt="p")


def test_streaming_retries_until_the_first_chunk():
    llm, calls = streaming([api_error(503), httpx.ReadTimeout("slow"), ["Every ", "timeline ", "ends."]])

    assert "".join(stream(llm)) == "Every timeline ends."
    assert calls == ["first", "first", "first"]


def test_streaming_falls_through_a_retired_model():
    llm, calls = streaming([api_error(404), ["ok"]])

    assert "".join(stream(llm)) == "ok"
    assert calls == ["first", "second"]


def test_an_error_after_the_answer_started_ends_it_instead_of_restarting():
    llm, calls = streaming([["Every ", api_error(503)]])
    received = []

    with pytest.raises(LLMError, match="cut off"):
        for chunk in stream(llm):
            received.append(chunk)

    assert received == ["Every "]
    assert calls == ["first"]


def test_make_llm_needs_a_key(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "gemini_api_key", None)

    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        make_llm()
    assert make_llm("request-key") is not None  # a per-request key is enough

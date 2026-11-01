import json
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
        return SimpleNamespace(text=outcome, usage_metadata=None)  # real responses always carry usage

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


def test_light_tasks_use_the_light_models():
    calls: list[str] = []

    def generate_content(*, model, contents, config):
        calls.append(model)
        return SimpleNamespace(text=OK, usage_metadata=None)

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    llm = GeminiLLM("key", ["flash"], light_models=["flash-lite"], client=client)

    llm.generate_json(system="s", prompt="p", schema=Answer)
    llm.generate_json(system="s", prompt="p", schema=Answer, light=True)

    assert calls == ["flash", "flash-lite"]


# --- The OpenAI-style adapter (Groq), against a fake HTTP server -------------------------


def groq(responses):
    """An OpenAICompatibleLLM whose server replays `responses` and records requests and waits."""
    requests, waits = [], []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return queue.pop(0)

    llm = llm_module.OpenAICompatibleLLM(
        "gsk-test", "openai/gpt-oss-120b",
        client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=waits.append,
    )  # fmt: skip
    return llm, requests, waits


def completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}], "usage": {}})


def test_groq_returns_validated_json_and_asks_for_the_schema():
    llm, requests, _ = groq([completion(OK)])

    assert ask(llm) == Answer(word="ok")
    body = json.loads(requests[0].content)
    assert requests[0].headers["authorization"] == "Bearer gsk-test"
    assert body["response_format"]["json_schema"]["schema"]["properties"]["word"]["type"] == "string"
    assert body["reasoning_effort"] == "low"


def test_groq_waits_as_long_as_a_rate_limit_asks_then_retries():
    limited = httpx.Response(429, headers={"retry-after": "7"})
    llm, requests, waits = groq([limited, completion("not json"), completion(OK)])

    assert ask(llm) == Answer(word="ok")
    assert waits == [7.0, 0] and len(requests) == 3  # the wait, then a malformed answer asked again


def test_groq_rejected_key_fails_immediately():
    llm, requests, _ = groq([httpx.Response(401)])

    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        ask(llm)
    assert len(requests) == 1


def test_groq_streams_server_sent_events():
    events = [
        'data: {"choices":[{"delta":{"role":"assistant"}}]}',
        'data: {"choices":[{"delta":{"content":"Kang "}}]}',
        'data: {"choices":[{"delta":{"content":"waits."}}]}',
        "data: [DONE]",
    ]
    llm, _, _ = groq([httpx.Response(200, text="\n\n".join(events) + "\n\n")])

    assert "".join(llm.stream_text(system="s", prompt="p")) == "Kang waits."


def test_no_groq_key_means_no_fallback(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "groq_api_key", "")
    assert llm_module.make_fallback_llm() is None


def test_a_used_up_daily_quota_moves_on_without_waiting(monkeypatch):
    daily = errors.APIError(429, {"error": {"code": 429, "message": "Quota exceeded: GenerateRequestsPerDayPerProjectPerModel-FreeTier", "status": "RESOURCE_EXHAUSTED"}})
    llm, calls = gemini([daily, OK])
    waits = []
    monkeypatch.setattr(llm_module.time, "sleep", waits.append)

    assert ask(llm) == Answer(word="ok")
    assert calls == ["first", "second"] and waits == []  # no retries against a quota that resets tomorrow


def test_plain_text_answers_for_line_labelling():
    llm, requests, _ = groq([completion("0|NARRATOR|neutral|1|normal|0|200|")])

    assert llm.generate_text(system="s", prompt="p", light=True).startswith("0|NARRATOR")
    assert "response_format" not in json.loads(requests[0].content)

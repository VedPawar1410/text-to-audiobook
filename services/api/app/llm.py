"""Thin LLM wrapper: system + prompt in, a validated Pydantic object out (or streamed text).

Gemini is the main provider (free key). Groq is an optional fallback for when Gemini is
overloaded: any OpenAI-style chat API works through the same small class (an Ollama
server on this machine would too). Handles what free tiers actually do: temporary 503
"high demand" errors, 429 rate limits, and models retired for new keys (404).
"""

import json
import logging
import time
from collections.abc import Iterator
from typing import Protocol, TypeVar

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.config import settings

T = TypeVar("T", bound=BaseModel)
log = logging.getLogger(__name__)

RETRYABLE = {429, 500, 502, 503, 504}
# Without a timeout a hung request blocks forever (seen while building PR 6).
# Generous enough for the whole-document pass on a long book.
REQUEST_TIMEOUT_MS = 120_000


class LLMError(RuntimeError):
    """The LLM couldn't produce a usable answer; the message is safe to show users."""


class LLM(Protocol):
    # light: a simpler, repetitive task (labelling lines) that a smaller model handles well
    def generate_json(self, *, system: str, prompt: str, schema: type[T], light: bool = False) -> T: ...

    def generate_text(self, *, system: str, prompt: str, light: bool = False) -> str: ...

    def stream_text(self, *, system: str, prompt: str) -> Iterator[str]: ...


def _daily_quota_gone(error: errors.APIError) -> bool:
    """A 429 for the free tier's requests per day: waiting seconds won't help, so move on."""
    return error.code == 429 and "PerDay" in str(error)


class GeminiLLM:
    # How much line labelling one request takes, and how many run at once
    batch_lines = 150
    parallel = 3

    def __init__(
        self,
        api_key: str,
        models: list[str],
        *,
        light_models: list[str] | None = None,
        attempts_per_model: int = 3,
        backoff_seconds: float = 2.0,
        client=None,
    ):
        self._client = client or genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)
        )
        self._models = models
        self._light_models = light_models or models
        self._attempts = attempts_per_model
        self._backoff = backoff_seconds

    def generate_json(self, *, system: str, prompt: str, schema: type[T], light: bool = False) -> T:
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.4,
            # Low thinking: ~2.5s per call instead of much longer, with good labels (PR 5 spike)
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        return self._generate(prompt, config, light, lambda text: schema.model_validate_json(text))

    def generate_text(self, *, system: str, prompt: str, light: bool = False) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.4,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        return self._generate(prompt, config, light, lambda text: text)

    def _generate(self, prompt: str, config, light: bool, parse):
        """Try each model in turn, retrying what's worth retrying; parse() may reject an answer."""
        last_error: Exception | None = None

        for model in self._light_models if light else self._models:
            for attempt in range(self._attempts):
                try:
                    response = self._client.models.generate_content(
                        model=model, contents=prompt, config=config
                    )
                    result = parse(response.text or "")
                    _log_usage(model, response.usage_metadata)
                    return result
                except errors.APIError as error:
                    last_error = error
                    if error.code == 404:
                        log.warning("Model %s unavailable (404); trying the next one", model)
                        break
                    if _daily_quota_gone(error):
                        log.warning("Daily free quota used up on %s; trying the next one", model)
                        break
                    if error.code in (401, 403):
                        raise LLMError("The Gemini API key was rejected. Check GEMINI_API_KEY.") from error
                    if error.code not in RETRYABLE:
                        raise LLMError(f"Gemini rejected the request ({error.code}): {error.message}") from error
                    log.warning("Gemini %s on %s (attempt %d)", error.code, model, attempt + 1)
                except ValidationError as error:  # malformed JSON: simply ask again
                    last_error = error
                    log.warning("Invalid JSON from %s (attempt %d)", model, attempt + 1)
                except httpx.TransportError as error:  # timeouts and dropped connections
                    last_error = error
                    log.warning("Network problem with %s (attempt %d): %r", model, attempt + 1, error)

                if attempt < self._attempts - 1:
                    time.sleep(self._backoff * 2**attempt)

        raise LLMError(f"The AI service is unavailable right now. Last error: {last_error}")

    def stream_text(self, *, system: str, prompt: str) -> Iterator[str]:
        """Plain text, chunk by chunk as the model writes it.

        Retries and model fallback apply until the first chunk arrives. After that the
        reader is already seeing the answer, so an error ends it instead of restarting.
        """
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.5,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        last_error: Exception | None = None

        for model in self._models:
            for attempt in range(self._attempts):
                started = False
                try:
                    for chunk in self._client.models.generate_content_stream(model=model, contents=prompt, config=config):
                        if chunk.text:
                            started = True
                            yield chunk.text
                    return
                except (errors.APIError, httpx.TransportError) as error:
                    if started:
                        raise LLMError("The answer was cut off. Please ask again.") from error
                    last_error = error
                    code = getattr(error, "code", None)
                    if code == 404 or (isinstance(error, errors.APIError) and _daily_quota_gone(error)):
                        break
                    if code in (401, 403):
                        raise LLMError("The Gemini API key was rejected. Check GEMINI_API_KEY.") from error
                    if code is not None and code not in RETRYABLE:
                        raise LLMError(f"Gemini rejected the request ({code}).") from error
                    log.warning("Streaming from %s failed (attempt %d): %r", model, attempt + 1, error)
                if attempt < self._attempts - 1:
                    time.sleep(self._backoff * 2**attempt)

        raise LLMError(f"The AI service is unavailable right now. Last error: {last_error}")


def _log_usage(model: str, usage) -> None:
    """Token counts per call: the numbers that decide speed and free-tier headroom."""
    if usage is not None:
        log.info(
            "%s: %s tokens in, %s out, %s thinking",
            model, usage.prompt_token_count, usage.candidates_token_count, usage.thoughts_token_count or 0,
        )  # fmt: skip


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MAX_RETRY_WAIT_SECONDS = 60  # a 429 says how long to wait; never wait longer than this


class OpenAICompatibleLLM:
    """Any OpenAI-style chat completions API, called with plain httpx (no SDK needed).

    Used for Groq: its free tier allows 8k tokens per minute, so line labelling sends
    fewer lines per request, one request at a time, and a 429 is answered by waiting as
    long as its retry-after header asks.
    """

    batch_lines = 100  # ~5k tokens a request, rows in and out: inside 8k tokens a minute
    parallel = 1

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = GROQ_BASE_URL,
        name: str = "Groq",
        attempts: int = 3,
        client: httpx.Client | None = None,
        sleep=time.sleep,
    ):
        self._model = model
        self._url = f"{base_url}/chat/completions"
        self._name = name
        self._attempts = attempts
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_MS / 1000)
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._sleep = sleep

    def _body(self, system: str, prompt: str, **extra) -> dict:
        return {
            "model": self._model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "reasoning_effort": "low",  # reasoning tokens count against the per-minute limit too
            **extra,
        }

    def _failure(self, response: httpx.Response, attempt: int) -> float | None:
        """Seconds to wait before retrying, or None when retrying can't help (raises instead)."""
        code = response.status_code
        if code in (401, 403):
            raise LLMError(f"The {self._name} API key was rejected. Check GROQ_API_KEY.")
        if code == 413:
            raise LLMError(f"Too much text for {self._name}'s free tier in one request.")
        if code == 429:
            return min(float(response.headers.get("retry-after") or 2**attempt * 5), MAX_RETRY_WAIT_SECONDS)
        if code >= 500:
            return 2.0 * 2**attempt
        raise LLMError(f"{self._name} rejected the request ({code}).")

    def generate_json(self, *, system: str, prompt: str, schema: type[T], light: bool = False) -> T:
        # Best-effort JSON schema: Groq's strict mode rejects common schema shapes; we validate anyway
        response_format = {"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()}}
        body = self._body(system, prompt, temperature=0.4, max_completion_tokens=4000, response_format=response_format)
        return self._complete(body, lambda text: schema.model_validate_json(text))

    def generate_text(self, *, system: str, prompt: str, light: bool = False) -> str:
        body = self._body(system, prompt, temperature=0.4, max_completion_tokens=3000)
        return self._complete(body, lambda text: text)

    def _complete(self, body: dict, parse):
        last_error: Exception | str | None = None
        for attempt in range(self._attempts):
            try:
                response = self._client.post(self._url, json=body, headers=self._headers)
                if response.status_code == 200:
                    data = response.json()
                    usage = data.get("usage", {})
                    log.info("%s %s: %s tokens in, %s out", self._name, self._model,
                             usage.get("prompt_tokens"), usage.get("completion_tokens"))  # fmt: skip
                    return parse(data["choices"][0]["message"]["content"] or "")
                last_error = f"HTTP {response.status_code}"
                wait = self._failure(response, attempt)
            except ValidationError as error:  # malformed JSON: simply ask again
                last_error, wait = error, 0
            except httpx.TransportError as error:
                last_error, wait = error, 2.0 * 2**attempt
            log.warning("%s attempt %d failed: %s", self._name, attempt + 1, last_error)
            if attempt < self._attempts - 1:
                self._sleep(wait)

        raise LLMError(f"{self._name} is unavailable right now. Last error: {last_error}")

    def stream_text(self, *, system: str, prompt: str) -> Iterator[str]:
        body = self._body(system, prompt, temperature=0.5, max_completion_tokens=1024, stream=True)
        last_error: Exception | str | None = None

        for attempt in range(self._attempts):
            started = False
            try:
                with self._client.stream("POST", self._url, json=body, headers=self._headers) as response:
                    if response.status_code != 200:
                        response.read()
                        last_error = f"HTTP {response.status_code}"
                        wait = self._failure(response, attempt)
                    else:
                        # Server-sent events: "data: {json}" lines, ending with "data: [DONE]"
                        for line in response.iter_lines():
                            if not line.startswith("data: ") or line == "data: [DONE]":
                                continue
                            text = json.loads(line[6:])["choices"][0]["delta"].get("content")
                            if text:
                                started = True
                                yield text
                        return
            except httpx.TransportError as error:
                if started:
                    raise LLMError("The answer was cut off. Please ask again.") from error
                last_error, wait = error, 2.0 * 2**attempt
            if attempt < self._attempts - 1:
                self._sleep(wait)

        raise LLMError(f"{self._name} is unavailable right now. Last error: {last_error}")


def make_llm(api_key: str | None = None) -> LLM:
    """The configured LLM, using a per-request key if given (bring-your-own-key)."""
    key = api_key or settings.gemini_api_key
    if not key:
        raise LLMError("No Gemini API key. Set GEMINI_API_KEY in services/api/.env.")
    # With a fallback configured, give up on an overloaded Gemini sooner and let it take over
    attempts = 2 if settings.groq_api_key else 3
    return GeminiLLM(key, settings.llm_models, light_models=settings.label_models, attempts_per_model=attempts)


def make_fallback_llm() -> LLM | None:
    """Groq, if a key is configured: used only when Gemini can't answer."""
    if not settings.groq_api_key:
        return None
    return OpenAICompatibleLLM(settings.groq_api_key, settings.groq_model)

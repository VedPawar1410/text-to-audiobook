"""Thin LLM wrapper: system + prompt in, a validated Pydantic object out.

Gemini today (free key). Another provider is one more class with the same method.
Handles what free-tier models actually do (seen while building PR 5): temporary
503 "high demand" errors, and models retired for new keys (404).
"""

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
    def generate_json(self, *, system: str, prompt: str, schema: type[T]) -> T: ...

    def stream_text(self, *, system: str, prompt: str) -> Iterator[str]: ...


class GeminiLLM:
    def __init__(
        self,
        api_key: str,
        models: list[str],
        *,
        attempts_per_model: int = 3,
        backoff_seconds: float = 2.0,
        client=None,
    ):
        self._client = client or genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)
        )
        self._models = models
        self._attempts = attempts_per_model
        self._backoff = backoff_seconds

    def generate_json(self, *, system: str, prompt: str, schema: type[T]) -> T:
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.4,
            # Low thinking: ~2.5s per call instead of much longer, with good labels (PR 5 spike)
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        last_error: Exception | None = None

        for model in self._models:
            for attempt in range(self._attempts):
                try:
                    response = self._client.models.generate_content(
                        model=model, contents=prompt, config=config
                    )
                    return schema.model_validate_json(response.text or "")
                except errors.APIError as error:
                    last_error = error
                    if error.code == 404:
                        log.warning("Model %s unavailable (404); trying the next one", model)
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
                    if code == 404:
                        break
                    if code in (401, 403):
                        raise LLMError("The Gemini API key was rejected. Check GEMINI_API_KEY.") from error
                    if code is not None and code not in RETRYABLE:
                        raise LLMError(f"Gemini rejected the request ({code}).") from error
                    log.warning("Streaming from %s failed (attempt %d): %r", model, attempt + 1, error)
                if attempt < self._attempts - 1:
                    time.sleep(self._backoff * 2**attempt)

        raise LLMError(f"The AI service is unavailable right now. Last error: {last_error}")


def make_llm(api_key: str | None = None) -> LLM:
    """The configured LLM, using a per-request key if given (bring-your-own-key)."""
    key = api_key or settings.gemini_api_key
    if not key:
        raise LLMError("No Gemini API key. Set GEMINI_API_KEY in services/api/.env.")
    return GeminiLLM(key, settings.llm_models)

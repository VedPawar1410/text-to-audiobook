from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables or services/api/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/text_to_audiobook"
    # "cpu" is faster than "mps" for Kokoro on an M1 (measured in PR 3)
    tts_device: str = "cpu"
    # Rendered audio: clip cache + chapter files (git-ignored)
    data_dir: Path = Path(__file__).resolve().parents[1] / "data"

    # Free key from aistudio.google.com. A request can override it with an X-LLM-Key header.
    gemini_api_key: str | None = None
    # Tried in order: a retired (404) or overloaded (503) model falls through to the next
    # (Flash's free tier allows only 20 requests a day; Flash-Lite is the last resort)
    llm_models: list[str] = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.5-flash-lite"]
    # Labelling lines is simpler and repetitive: the lighter models are faster, have more
    # free requests per day, and are overloaded less often
    label_models: list[str] = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest"]

    # Optional fallback when Gemini is overloaded (free key from console.groq.com)
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    # Who labels lines first; the other (when configured) takes over the chunks that fail.
    # Gemini is more expressive; Groq is much faster (PR 16 comparison)
    label_provider: Literal["gemini", "groq"] = "gemini"


settings = Settings()

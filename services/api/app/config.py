from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables or services/api/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/text_to_audiobook"
    # "cpu" is faster than "mps" for Kokoro on an M1 (measured in PR 3)
    tts_device: str = "cpu"

    # Free key from aistudio.google.com. A request can override it with an X-LLM-Key header.
    gemini_api_key: str | None = None
    # Tried in order: a retired (404) or overloaded (503) model falls through to the next
    llm_models: list[str] = ["gemini-3.5-flash", "gemini-flash-latest"]


settings = Settings()

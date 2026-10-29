from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables or services/api/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/text_to_audiobook"
    # "cpu" is faster than "mps" for Kokoro on an M1 (measured in PR 3)
    tts_device: str = "cpu"


settings = Settings()

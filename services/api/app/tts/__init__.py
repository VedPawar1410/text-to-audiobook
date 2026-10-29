from functools import lru_cache

from app.config import settings
from app.tts.base import TTSEngine


@lru_cache
def get_engine() -> TTSEngine:
    """The app's single TTS engine (also used as a FastAPI dependency).

    Imported lazily: loading torch takes seconds, and the API should start instantly.
    """
    from app.tts.kokoro_engine import KokoroEngine

    return KokoroEngine(device=settings.tts_device)

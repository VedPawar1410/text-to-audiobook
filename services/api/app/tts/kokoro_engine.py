"""Kokoro-82M: free, local, Apache-2.0 TTS.

Measured on an M1: ~2.5x realtime on CPU, faster than MPS for this small model,
so CPU is the default (see settings.tts_device).
"""

import threading

import numpy as np
from kokoro import KModel, KPipeline

from app.tts.base import RenderResult, Voice
from app.tts.timing import Token, merge_chunks, trim_to_speech

REPO_ID = "hexgrad/Kokoro-82M"
SAMPLE_RATE = 24_000

# The 28 English voices in the model repo. Id format: <a|b accent><f|m gender>_<name>.
VOICE_IDS = [
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica", "af_kore", "af_nicole",
    "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx",
    "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
]  # fmt: skip


def _voice(voice_id: str) -> Voice:
    return Voice(
        id=voice_id,
        name=voice_id.split("_", 1)[1].capitalize(),
        gender="female" if voice_id[1] == "f" else "male",
        accent="American" if voice_id[0] == "a" else "British",
    )


VOICES = [_voice(v) for v in VOICE_IDS]


class KokoroEngine:
    name = "kokoro"

    def __init__(self, device: str = "cpu"):
        self._device = device
        self._model: KModel | None = None
        self._pipelines: dict[str, KPipeline] = {}
        # A torch model isn't safe to call from several threads at once.
        self._lock = threading.Lock()

    def voices(self) -> list[Voice]:
        return VOICES

    def _pipeline(self, lang_code: str) -> KPipeline:
        # One shared model (loaded on first use, ~4s); one light text pipeline per accent.
        if self._model is None:
            self._model = KModel(repo_id=REPO_ID).to(self._device).eval()
        if lang_code not in self._pipelines:
            self._pipelines[lang_code] = KPipeline(
                lang_code=lang_code, repo_id=REPO_ID, model=self._model
            )
        return self._pipelines[lang_code]

    def render(self, text: str, voice: str, speed: float = 1.0) -> RenderResult:
        if voice not in VOICE_IDS:
            raise ValueError(f"Unknown Kokoro voice: {voice}")

        audio_parts: list[np.ndarray] = []
        chunks: list[tuple[list[Token], float]] = []
        with self._lock:
            pipeline = self._pipeline(lang_code=voice[0])
            for result in pipeline(text, voice=voice, speed=speed):
                samples = result.audio.cpu().numpy()
                audio_parts.append(samples)
                tokens = [
                    Token(t.text, t.start_ts, t.end_ts, t.whitespace)
                    for t in (result.tokens or [])
                ]
                chunks.append((tokens, len(samples) / SAMPLE_RATE))

        audio = np.concatenate(audio_parts) if audio_parts else np.zeros(0, dtype=np.float32)
        audio, words = trim_to_speech(audio, SAMPLE_RATE, merge_chunks(chunks))
        return RenderResult(audio=audio, sample_rate=SAMPLE_RATE, words=words)

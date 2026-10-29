"""Kokoro's English voices. A light module (no torch import), so casting can use it cheaply."""

from app.tts.base import Voice

# The 28 English voices in the model repo. Id format: <a|b accent><f|m gender>_<name>.
VOICE_IDS = [
    "af_alloy", "af_aoede", "af_bella", "af_heart", "af_jessica", "af_kore", "af_nicole",
    "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx",
    "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
]  # fmt: skip

# Best first, following the quality grades in Kokoro's VOICES.md. Auto-casting
# walks this list, so the narrator and main characters get the strongest voices.
QUALITY_ORDER = [
    "af_heart", "af_bella", "bf_emma", "af_nicole", "am_fenrir", "am_michael", "am_puck",
    "af_aoede", "af_kore", "af_sarah", "bm_george", "bm_fable", "bf_isabella", "af_nova",
    "af_alloy", "af_sky", "bm_lewis", "am_echo", "am_eric", "am_liam", "am_onyx",
    "af_jessica", "af_river", "bf_alice", "bf_lily", "bm_daniel", "am_adam", "am_santa",
]  # fmt: skip


def _voice(voice_id: str) -> Voice:
    return Voice(
        id=voice_id,
        name=voice_id.split("_", 1)[1].capitalize(),
        gender="female" if voice_id[1] == "f" else "male",
        accent="American" if voice_id[0] == "a" else "British",
    )


VOICES = [_voice(v) for v in VOICE_IDS]
VOICES_BY_ID = {v.id: v for v in VOICES}

"""Real-model checks. Slower (model load ~5s); skip with: pytest -m "not kokoro"."""

import pytest

from app.tts.kokoro_engine import KokoroEngine

pytestmark = pytest.mark.kokoro

TEXT = "Every timeline ends. The only question is who will be standing there when it does."


@pytest.fixture(scope="module")
def engine():
    return KokoroEngine(device="cpu")


def test_words_match_the_text_and_move_forward(engine):
    result = engine.render(TEXT, "am_onyx")

    assert [w.text for w in result.words] == TEXT.split()
    starts = [w.start for w in result.words]
    assert starts == sorted(starts)
    assert all(w.end >= w.start for w in result.words)
    assert result.words[-1].end <= result.duration


def test_leading_silence_is_trimmed(engine):
    result = engine.render(TEXT, "am_onyx")

    assert result.words[0].start < 0.1


def test_slower_speed_gives_longer_audio(engine):
    normal = engine.render(TEXT, "am_onyx", speed=1.0)
    slow = engine.render(TEXT, "am_onyx", speed=0.8)

    assert slow.duration > normal.duration * 1.1


def test_british_voice_uses_its_own_pipeline(engine):
    result = engine.render("Good evening.", "bm_george")

    assert [w.text for w in result.words] == ["Good", "evening."]


def test_unknown_voice_is_rejected(engine):
    with pytest.raises(ValueError):
        engine.render("Hi.", "xx_nobody")

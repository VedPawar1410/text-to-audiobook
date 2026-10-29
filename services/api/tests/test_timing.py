import numpy as np
import pytest

from app.tts.base import WordTiming
from app.tts.timing import Token, merge_chunks, trim_to_speech


def test_punctuation_is_glued_to_its_word():
    tokens = [
        Token("Every", 0.2, 0.5, " "),
        Token("timeline", 0.5, 1.0, " "),
        Token("ends", 1.0, 1.4, ""),
        Token(".", 1.4, 1.5, " "),
        Token("Kang", 1.5, 1.8, ""),
        Token(",", 1.8, 1.9, " "),
    ]

    words = merge_chunks([(tokens, 2.0)])

    assert [w.text for w in words] == ["Every", "timeline", "ends.", "Kang,"]
    assert words[2] == WordTiming("ends.", 1.0, 1.5)


def test_opening_quote_is_glued_to_the_following_word():
    tokens = [Token('"', 0.1, 0.15, ""), Token("You", 0.15, 0.4, ""), Token('"', 0.4, 0.45, " ")]

    words = merge_chunks([(tokens, 1.0)])

    assert [w.text for w in words] == ['"You"']
    assert words[0].start == 0.1


def test_later_chunks_are_offset_and_never_glued_across():
    first = [Token("One", 0.0, 0.4, ""), Token(".", 0.4, 0.5, "")]  # no trailing space
    second = [Token("Two", 0.1, 0.5, "")]

    words = merge_chunks([(first, 1.0), (second, 1.0)])

    assert [w.text for w in words] == ["One.", "Two"]
    assert words[1].start == 1.1
    assert words[1].end == 1.5


def test_untimed_token_falls_back_to_previous_end():
    tokens = [Token("Hello", 0.0, 0.5, " "), Token("there", None, None, "")]

    words = merge_chunks([(tokens, 1.0)])

    assert words[1] == WordTiming("there", 0.5, 0.5)


def test_trim_removes_leading_and_trailing_silence():
    sample_rate = 100
    audio = np.zeros(300, dtype=np.float32)  # 3 seconds
    words = [WordTiming("Hi", 1.0, 1.5), WordTiming("there.", 1.5, 2.0)]

    trimmed, shifted = trim_to_speech(audio, sample_rate, words, lead=0.1, tail=0.2)

    assert len(trimmed) == 130  # 0.9s .. 2.2s
    assert shifted[0].text == "Hi"
    assert (shifted[0].start, shifted[0].end) == pytest.approx((0.1, 0.6))
    assert shifted[1].end == pytest.approx(1.1)


def test_trim_without_words_returns_audio_unchanged():
    audio = np.ones(10, dtype=np.float32)

    trimmed, words = trim_to_speech(audio, 100, [])

    assert len(trimmed) == 10 and words == []

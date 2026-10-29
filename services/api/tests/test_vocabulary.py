from pathlib import Path
from typing import get_args

from app.director.vocabulary import EMOTIONS, GENRES, EmotionName, GenreName

GUIDE = Path(__file__).parents[3] / "docs" / "narration-guide.md"


def test_tables_match_the_schema_enums():
    assert list(EMOTIONS) == list(get_args(EmotionName))
    assert list(GENRES) == list(get_args(GenreName))


def test_every_emotion_is_documented_in_the_narration_guide():
    # Keeps the human guide and the machine vocabulary from drifting apart
    guide = GUIDE.read_text()

    assert all(f"`{name}`" in guide for name in EMOTIONS)


def test_speeds_stay_in_the_range_kokoro_sounds_natural():
    assert all(0.75 <= e.speed <= 1.25 for e in EMOTIONS.values())

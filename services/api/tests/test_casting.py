from collections import Counter

from app.director.casting import auto_cast
from app.director.director import NARRATOR
from app.tts.kokoro_voices import VOICES_BY_ID
from tests.fakes import cast_member, direction


def test_narrator_gets_the_best_voice_that_fits():
    assert auto_cast(direction(narrator_gender="female", narrator_accent="american", cast=[]))[0].voice == "af_heart"
    assert auto_cast(direction(narrator_gender="male", narrator_accent="british", cast=[]))[0].voice == "bm_george"


def test_every_role_gets_its_own_voice_while_possible():
    plans = auto_cast(direction(cast=[cast_member("KANG"), cast_member("THOR"), cast_member("WANDA", gender="female")]))

    assert [p.cast_id for p in plans] == [NARRATOR, "KANG", "THOR", "WANDA"]
    assert len({p.voice for p in plans}) == 4
    assert VOICES_BY_ID[plans[3].voice].gender == "female"


def test_accent_relaxes_but_gender_never_does():
    cast = [cast_member(f"QUEEN{i}", gender="female", accent="british") for i in range(5)]

    plans = auto_cast(direction(narrator_gender="female", narrator_accent="british", cast=cast))

    voices = [VOICES_BY_ID[p.voice] for p in plans]
    assert all(v.gender == "female" for v in voices)
    assert sum(v.accent == "British" for v in voices) == 4  # every British female voice is used first
    assert len({p.voice for p in plans}) == 6


def test_voices_are_reused_evenly_once_the_pool_runs_out():
    cast = [cast_member(f"SOLDIER{i}") for i in range(20)]

    plans = auto_cast(direction(cast=cast))

    uses = Counter(p.voice for p in plans)
    assert all(VOICES_BY_ID[v].gender == "male" for v in uses)
    assert max(uses.values()) - min(uses.values()) <= 1


def test_age_sets_speed_and_the_novelty_voice_is_never_auto_cast():
    cast = [cast_member("ELDER", age="elder"), cast_member("KID", age="child")] + [
        cast_member(f"EXTRA{i}") for i in range(30)
    ]

    plans = {p.cast_id: p for p in auto_cast(direction(cast=cast))}

    assert plans["ELDER"].speed < 1 < plans["KID"].speed
    assert "am_santa" not in {p.voice for p in plans.values()}

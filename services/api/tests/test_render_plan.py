from types import SimpleNamespace

import pytest

from app.render.performance import (
    GAP_BEFORE_KIND_MS,
    PARAGRAPH_GAP_MS,
    SCENE_BREAK_MS,
    TRANSITION_MS,
    fingerprint,
    plan_chapter,
    speed_for,
)
from app.render.speech import speech_text

VOICES = {"NARRATOR": ("bm_george", 1.0), "KANG": ("am_michael", 0.95)}


def seg(id, block, kind="paragraph", text="A line.", role="NARRATOR", emotion="neutral", intensity=1, pace="normal", before=0, after=0):
    return SimpleNamespace(
        id=id, block_index=block, block_kind=kind, text=text, role=role, emotion=emotion,
        intensity=intensity, pace=pace, pause_before_ms=before, pause_after_ms=after,
    )  # fmt: skip


def test_speed_combines_persona_emotion_intensity_and_pace():
    assert speed_for("neutral", 1, "normal", 1.0) == 1.0
    assert speed_for("ominous", 2, "normal", 1.0) == 0.85  # the table value at intensity 2
    assert speed_for("ominous", 1, "normal", 1.0) == 0.93  # half the deviation at intensity 1
    assert speed_for("ominous", 2, "slow", 1.0) == pytest.approx(0.78)  # 0.85 x 0.92
    assert speed_for("urgent", 3, "fast", 1.2) == 1.25  # clamped: Kokoro sounds wrong beyond
    assert speed_for("grief", 3, "slow", 0.8) == 0.75
    assert speed_for("made-up", 1, "normal", 1.0) == 1.0  # unknown emotion falls back to neutral


def test_spoken_form_of_scene_headings_and_transitions():
    assert speech_text("scene_heading", "INT. CITADEL THRONE ROOM - NIGHT") == "Interior. Citadel throne room. Night."
    assert speech_text("scene_heading", "EXT. THE VOID - CONTINUOUS") == "Exterior. The void. Continuous."
    assert speech_text("scene_heading", "Scene 1 - The Citadel") == "Scene 1 - The Citadel"
    assert speech_text("transition", "CUT TO:") is None
    assert speech_text("scene_break", "") is None
    assert speech_text("dialogue", "THOR!") == "THOR!"  # Kokoro reads capitals as words, not letters


def test_silence_follows_structure_and_direction():
    steps = plan_chapter(
        [
            seg(1, 0, "heading", "Chapter One"),
            seg(2, 1, text="First sentence.", after=300),
            seg(3, 1, text="Same paragraph."),
            seg(4, 2, text="New paragraph.", before=500),
            seg(5, 3, "scene_break", ""),
            seg(6, 4, "transition", "CUT TO:"),
        ],
        VOICES,
        "prose",
    )

    assert [s.silence_before_ms for s in steps] == [
        0,  # chapter start
        PARAGRAPH_GAP_MS["prose"],  # after the heading block
        300,  # same paragraph: just the director's pause after the previous line
        PARAGRAPH_GAP_MS["prose"] + 500,  # paragraph gap + the director's pause before
        PARAGRAPH_GAP_MS["prose"],
        PARAGRAPH_GAP_MS["prose"],
    ]
    assert (steps[4].speech, steps[4].silent_ms) == (None, SCENE_BREAK_MS)
    assert (steps[5].speech, steps[5].silent_ms) == (None, TRANSITION_MS)


def test_headings_get_a_longer_gap_than_paragraphs():
    steps = plan_chapter([seg(1, 0), seg(2, 1, "scene_heading", "INT. HALL - DAY")], VOICES, "screenplay")

    assert steps[1].silence_before_ms == GAP_BEFORE_KIND_MS["scene_heading"]
    assert steps[1].speech == "Interior. Hall. Day."


def test_voices_come_from_the_role_with_narrator_fallback():
    steps = plan_chapter(
        [seg(1, 0, role="KANG", emotion="cold", intensity=2), seg(2, 1, role="UNCAST")], VOICES, "screenplay"
    )

    assert (steps[0].voice, steps[0].speed) == ("am_michael", round(0.95 * 0.93, 2))
    assert steps[1].voice == "bm_george"


def test_fingerprint_changes_only_when_the_audio_would():
    base = [seg(1, 0, text="Hello there.")]

    same = fingerprint(plan_chapter(base, VOICES, "prose"))
    assert fingerprint(plan_chapter(base, VOICES, "prose")) == same
    assert fingerprint(plan_chapter(base, {"NARRATOR": ("af_heart", 1.0)}, "prose")) != same
    assert fingerprint(plan_chapter([seg(1, 0, text="Hello there.", emotion="angry")], VOICES, "prose")) != same

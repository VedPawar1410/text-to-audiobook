import numpy as np
import pytest
import soundfile as sf

from app.render.assembly import SAMPLE_RATE, Mp3Writer, assemble
from app.render.performance import CHAPTER_TAIL_MS, Step
from tests.fakes import FakeEngine

STEPS = [
    Step(10, 0, "One two.", voice="v", speed=1.0),  # 0.4 s
    Step(11, 500, "Three.", voice="v", speed=2.0),  # 0.1 s, after 0.5 s of silence
    Step(12, 250, None, silent_ms=1500),  # a scene break
]


def test_manifest_times_every_line_and_word():
    chunks = []

    manifest = assemble(STEPS, FakeEngine().render, chunks.append)

    one, three, gap = manifest["segments"]
    assert (one["segment_id"], one["start"], one["end"]) == (10, 0.0, 0.4)
    assert [(w["text"], w["start"], w["end"]) for w in one["words"]] == [("One", 0.0, 0.2), ("two.", 0.2, 0.4)]
    assert (three["start"], three["end"]) == (0.9, 1.0)
    assert three["words"][0]["start"] == 0.9  # word times are on the chapter's timeline
    assert (gap["start"], gap["end"], gap["words"]) == (1.25, 2.75, [])
    assert manifest["duration"] == pytest.approx(2.75 + CHAPTER_TAIL_MS / 1000)
    assert sum(len(c) for c in chunks) == round(manifest["duration"] * SAMPLE_RATE)


def test_audio_is_streamed_in_pieces_not_built_in_memory():
    chunks = []

    assemble(STEPS, FakeEngine().render, chunks.append)

    assert len(chunks) > 3


def test_mp3_matches_the_manifest_duration(tmp_path):
    path = tmp_path / "chapter.mp3"

    with Mp3Writer(path) as writer:
        manifest = assemble(STEPS, FakeEngine().render, writer.write)

    assert sf.info(path).duration == pytest.approx(manifest["duration"], abs=0.1)
    assert not (tmp_path / "chapter.mp3.tmp").exists()


def test_a_failed_chapter_leaves_no_partial_file(tmp_path):
    path = tmp_path / "chapter.mp3"

    with pytest.raises(RuntimeError), Mp3Writer(path) as writer:
        writer.write(np.zeros(1000, dtype=np.float32))
        raise RuntimeError("synthesis exploded")

    assert list(tmp_path.iterdir()) == []

import pytest

from app.director.director import CHUNK_LINES, NARRATOR, Line, direct_document, direct_lines
from app.llm import LLMError
from tests.fakes import FakeLLM, cast_member, direction, label

SCRIPT = [
    Line(0, "scene_heading", "INT. CITADEL - NIGHT"),
    Line(1, "action", "A vast hall."),
    Line(2, "dialogue", "You came.", "KANG", "voice-over"),
    Line(3, "scene_break", ""),
    Line(4, "dialogue", "Where are the others?", "THOR", "angry"),
]


def test_parser_speakers_win_over_the_llm():
    # The LLM claims THOR says everything; the parser knows better
    llm = FakeLLM(labeller=lambda i: label(i, speaker="THOR"))

    performances = direct_lines(llm, direction(), SCRIPT)

    assert [p.role for p in performances] == [NARRATOR, NARRATOR, "KANG", NARRATOR, "THOR"]


def test_prose_speakers_come_from_the_llm_but_only_cast_members():
    lines = [
        Line(0, "paragraph", '"You came," he said.'),
        Line(1, "paragraph", "The hall was dark."),
        Line(2, "paragraph", '"Hello?"'),
    ]
    proposed = {0: "kang", 1: "NARRATOR", 2: "STRANGER"}

    performances = direct_lines(FakeLLM(labeller=lambda i: label(i, speaker=proposed[i])), direction(), lines)

    assert [p.role for p in performances] == ["KANG", NARRATOR, NARRATOR]


def test_out_of_range_values_are_clamped_and_emphasis_filtered():
    line = Line(0, "dialogue", "You came, Odinson.", "KANG")
    wild = label(0, intensity=9, pause_before_ms=-50, pause_after_ms=99_999, emphasis=["came", "invented", "You", "Odinson"])

    (performance,) = direct_lines(FakeLLM(labeller=lambda i: wild), direction(), [line])

    assert performance.intensity == 3
    assert (performance.pause_before_ms, performance.pause_after_ms) == (0, 3000)
    assert performance.emphasis == ["came", "You"]  # only words in the line, at most two


def test_skipped_lines_get_defaults_and_are_flagged():
    performances = direct_lines(FakeLLM(labeller=lambda i: label(i, emotion="angry"), skip={2}), direction(), SCRIPT)

    assert performances[2].labelled is False
    assert (performances[2].role, performances[2].emotion) == ("KANG", "neutral")
    assert performances[4].emotion == "angry"


def test_scene_breaks_are_not_sent_to_the_llm():
    llm = FakeLLM()

    performances = direct_lines(llm, direction(), SCRIPT)

    assert "[3]" not in llm.line_prompts[0]
    assert performances[3].labelled is True and performances[3].emotion == "neutral"


def test_long_texts_are_chunked_and_later_chunks_get_context():
    lines = [Line(i, "paragraph", f"Sentence number {i}.") for i in range(CHUNK_LINES * 2 + 10)]
    llm = FakeLLM()

    performances = direct_lines(llm, direction(cast=[]), lines)

    assert len(llm.line_prompts) == 3
    assert sum("Context, already performed" in p for p in llm.line_prompts) == 2
    assert all(p.labelled for p in performances)


def test_a_failed_chunk_falls_back_to_defaults_for_its_lines_only():
    lines = [Line(i, "paragraph", f"Sentence {i}.") for i in range(CHUNK_LINES + 5)]

    performances = direct_lines(FakeLLM(fail_chunks_starting_at={CHUNK_LINES}), direction(cast=[]), lines)

    assert all(p.labelled for p in performances[:CHUNK_LINES])
    assert not any(p.labelled for p in performances[CHUNK_LINES:])


def test_nothing_labelled_at_all_is_an_error():
    with pytest.raises(LLMError):
        direct_lines(FakeLLM(fail_chunks_starting_at={0}), direction(), SCRIPT)


def test_document_pass_normalises_ids_and_adds_missing_parser_speakers():
    llm = FakeLLM(document=direction(cast=[cast_member(" kang ")]))

    result = direct_document(llm, title="The Citadel", format="screenplay", speakers=["KANG", "THOR"], lines=SCRIPT)

    assert [m.id for m in result.cast] == ["KANG", "THOR"]
    assert "KANG, THOR" in llm.prompts[0]  # the prompt pins the parser's speaker ids
    assert "scifi_action" in llm.prompts[0]  # and offers the genre list

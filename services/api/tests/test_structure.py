from pathlib import Path

from app.structure import parse_text

FIXTURES = Path(__file__).parent / "fixtures"


def blocks(document):
    return [block for section in document.sections for block in section.blocks]


def test_formal_screenplay_structure():
    doc = parse_text((FIXTURES / "citadel_screenplay.txt").read_text())

    assert doc.format == "screenplay"
    assert doc.title == "THE CITADEL AT THE END OF TIME"
    assert [s.title for s in doc.sections] == [
        None,  # "FADE IN:" comes before the first scene
        "INT. CITADEL THRONE ROOM - NIGHT",
        "EXT. THE VOID - CONTINUOUS",
    ]
    assert doc.stats.speakers == ["KANG", "THOR"]


def test_screenplay_dialogue_speaker_and_direction():
    dialogue = [b for b in blocks(parse_text((FIXTURES / "citadel_screenplay.txt").read_text())) if b.kind == "dialogue"]

    assert [(b.speaker, b.direction, b.text) for b in dialogue] == [
        ("KANG", "voice-over", "You came. They always come."),
        ("THOR", "through gritted teeth", "Where are the others?"),
        ("THOR", "beat", "Answer me!"),  # a mid-speech parenthetical starts a new block
        ("KANG", None, "Every timeline ends, Odinson. The only question is who will be standing there when it does."),
    ]


def test_screenplay_action_with_colon_is_not_a_speaker():
    doc = parse_text((FIXTURES / "citadel_screenplay.txt").read_text())

    first_action = next(b for b in blocks(doc) if b.kind == "action")
    assert first_action.text.startswith("A vast hall of green and gold. The Council:")
    assert "THE COUNCIL" not in doc.stats.speakers


def test_scene_headings_and_transitions_are_single_sentences():
    doc = parse_text((FIXTURES / "citadel_screenplay.txt").read_text())

    heading = next(b for b in blocks(doc) if b.kind == "scene_heading")
    assert heading.sentences == ["INT. CITADEL THRONE ROOM - NIGHT"]
    assert [b.text for b in blocks(doc) if b.kind == "transition"] == ["FADE IN:", "CUT TO:"]


def test_colon_style_fan_script():
    doc = parse_text((FIXTURES / "citadel_fan_script.txt").read_text())

    assert doc.format == "screenplay"
    assert [s.title for s in doc.sections] == ["Scene 1 - The Citadel", "Scene 2 - The Void"]
    assert doc.stats.speakers == ["KANG", "THOR", "STRANGE", "WANDA"]
    spoken = [(b.kind, b.speaker, b.direction, b.text) for b in blocks(doc) if b.kind != "scene_heading"]
    assert spoken[1] == ("dialogue", "THOR", "angry", "Not this one.")
    # a wrapped line continues the dialogue...
    assert spoken[2][3] == "The only question is who will be standing there when it does."
    # ...but a standalone parenthetical is stage action, not part of Kang's line
    assert spoken[3] == ("action", None, None, "Kang smiles")


def test_markdown_prose_structure():
    doc = parse_text((FIXTURES / "last_timeline.md").read_text())

    assert doc.format == "prose"
    assert doc.title == "The Last Timeline"
    assert [s.title for s in doc.sections] == ["Chapter One", "Chapter Two"]
    assert [b.kind for b in doc.sections[0].blocks] == [
        "heading", "paragraph", "quote", "scene_break", "paragraph", "list_item", "list_item",
    ]  # fmt: skip


def test_prose_cleans_markdown_and_keeps_abbreviations_together():
    doc = parse_text((FIXTURES / "last_timeline.md").read_text())

    paragraph = doc.sections[0].blocks[1]
    assert paragraph.text == (
        "It was dark in the citadel. Dr. Strange arrived at 3 p.m. and found the door already open."
    )
    assert paragraph.sentences == [
        "It was dark in the citadel.",
        "Dr. Strange arrived at 3 p.m. and found the door already open.",
    ]
    assert doc.sections[0].blocks[6].text == "Second, the war that followed."


def test_plain_text_chapters_without_markdown():
    text = "Chapter 1\n\nThe hall was empty.\n\nChapter 2\n\nThen he arrived."

    doc = parse_text(text)

    assert [s.title for s in doc.sections] == ["Chapter 1", "Chapter 2"]


def test_leading_title_line_and_given_title_fallback():
    assert parse_text("My Story\n\nOnce upon a time.").title == "My Story"
    assert parse_text("Once upon a time.", title="upload").title == "upload"
    assert parse_text("Title: The Kang Dynasty\n\nIt begins.").title == "The Kang Dynasty"


def test_stats_and_estimated_minutes():
    doc = parse_text(" ".join(["word"] * 300) + ".")

    assert doc.stats.words == 300
    assert doc.stats.estimated_minutes == 2.0  # 150 words per minute


def test_long_text_has_no_limit():
    paragraph = "The council met again, and again the vote was close. "
    text = "\n\n".join([paragraph * 5] * 400)  # ~105k characters, well past Evernote's 15k cap

    doc = parse_text(text)

    assert doc.stats.characters > 100_000
    assert doc.stats.sentences == 400 * 5

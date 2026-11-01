from pathlib import Path

from app.structure import clean_title, parse_text

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


def test_a_long_text_without_headings_is_cut_into_parts_between_paragraphs():
    paragraph = " ".join(["word"] * 99) + " end."  # 100 words
    doc = parse_text("\n\n".join([paragraph] * 40))  # 4,000 words, no headings

    assert [s.title for s in doc.sections] == ["Part 1", "Part 2", "Part 3"]
    assert [sum(len(b.text.split()) for b in s.blocks) for s in doc.sections] == [1500, 1500, 1000]
    assert doc.stats.words == 4000  # nothing lost or duplicated


def test_a_short_tail_joins_the_part_before_and_short_chapters_stay_whole():
    paragraph = " ".join(["word"] * 99) + " end."
    tail = "\n\n".join([paragraph] * 34)  # 3,400 words: the last 400 would be a stub part

    doc = parse_text("# The Book\n\n## Chapter One\n\n" + "\n\n".join([paragraph] * 20) + "\n\n## Chapter Two\n\n" + tail)

    assert [s.title for s in doc.sections] == ["Chapter One", "Chapter Two · Part 1", "Chapter Two · Part 2"]


def test_titles_from_file_metadata_are_cleaned():
    assert clean_title("Microsoft Word - All Tomorrows.doc") == "All Tomorrows"
    assert clean_title("my_field_notes") == "my field notes"
    assert clean_title("The Kang Dynasty: a fan script.pdf") == "The Kang Dynasty: a fan script"
    assert clean_title("Word - by word") == "Word - by word"  # only known app prefixes are stripped
    assert clean_title("   ") is None


def test_an_author_named_near_the_top_is_found():
    doc = parse_text("All Tomorrows\n\nby C. M. Kosemen\n\nA billion years of human evolution, told as history.")

    assert doc.title == "All Tomorrows"
    assert doc.author == "C. M. Kosemen"
    assert parse_text("The bridge was built by hand.\n\nNobody remembers who.").author is None
    assert parse_text("Some text.", author="  Given Author ").author == "Given Author"


def test_a_byline_on_the_first_line_is_never_taken_as_the_title():
    doc = parse_text("by Ana Ruiz\n\nThe harbour was quiet.", title="Microsoft Word - Harbour Notes.doc")

    assert (doc.title, doc.author) == ("Harbour Notes", "Ana Ruiz")

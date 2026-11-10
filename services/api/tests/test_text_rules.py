"""Step 2 of the revive: headings, paragraphs and junk in pasted and plain-text books."""

from app.structure import clean_title, parse_text
from app.structure.cleanup import drop_contents, strip_gutenberg
from app.structure.prose import clean_inline

LONG = "The harbour was quiet that night, and nobody on the quay said a word about the ship. " * 2


def blocks(document):
    return [(b.kind, b.text) for s in document.sections for b in s.blocks]


def headings(document):
    return [text for kind, text in blocks(document) if kind == "heading"]


def test_a_heading_glued_to_its_text_is_split_off():
    doc = parse_text(f"My Plot\n\nAct One:\n{LONG}\n\nAct Two:\n{LONG}")
    assert [s.title for s in doc.sections] == ["Act One:", "Act Two:"]
    assert blocks(doc)[1] == ("paragraph", LONG.strip())


def test_single_line_breaks_between_long_lines_mean_one_paragraph_per_line():
    doc = parse_text(f"Act One:\n{LONG}\n\"Yes.\"\n{LONG}\nPost-Credits Scene:\n{LONG}")
    assert [kind for kind, _ in blocks(doc)] == ["heading", "paragraph", "paragraph", "paragraph", "heading", "paragraph"]
    assert headings(doc) == ["Act One:", "Post-Credits Scene:"]


def test_hard_wrapped_lines_are_still_joined_and_wrapped_starts_are_not_headings():
    wrapped = "Part of the reason was that the harbour master\nhad gone home early, and the lamp was out."
    doc = parse_text(f"Chapter 1\n\n{wrapped}")
    assert blocks(doc) == [("heading", "Chapter 1"), ("paragraph", wrapped.replace("\n", " "))]


def test_roman_numeral_and_caps_headings_with_sub_headings():
    text = f"I. A SCANDAL IN BOHEMIA\n\nI.\n\n{LONG}\n\nTHE FIRST NIGHT\n\n{LONG}\n\nII. THE RED-HEADED LEAGUE\n\n{LONG}"
    doc = parse_text(text)
    assert [s.title for s in doc.sections] == ["I. A SCANDAL IN BOHEMIA", "II. THE RED-HEADED LEAGUE"]
    assert headings(doc) == ["I. A SCANDAL IN BOHEMIA", "I.", "THE FIRST NIGHT", "II. THE RED-HEADED LEAGUE"]


def test_bare_word_titles_become_chapters_when_there_are_no_numbered_ones():
    doc = parse_text(f"Harbour Tales\n\nThe Harbour\n\n{LONG}\n\n\"Yes.\"\n\nA Letter from the Hill\n\n{LONG}")
    assert [s.title for s in doc.sections] == ["The Harbour", "A Letter from the Hill"]
    assert ("paragraph", '"Yes."') in blocks(doc)  # one-line dialogue is never a heading


def test_sentence_like_short_lines_stay_paragraphs():
    for line in ["What he remembered afterwards:", "He said:", "The end.", "by Ana Ruiz", "It was cold, and"]:
        doc = parse_text(f"# Book\n\n## Chapter One\n\n{line}\n\n{LONG}")
        assert headings(doc) == ["Chapter One"], line


def test_gutenberg_licence_is_removed_and_its_header_kept_as_metadata():
    text = (
        "The Project Gutenberg eBook of Harbour Tales\n\nThis ebook is for the use of anyone anywhere.\n\n"
        "Title: Harbour Tales\n\nAuthor: Ana Ruiz\n\n*** START OF THE PROJECT GUTENBERG EBOOK HARBOUR TALES ***\n\n"
        f"Chapter 1\n\n{LONG}\n\n*** END OF THE PROJECT GUTENBERG EBOOK HARBOUR TALES ***\n\nSection 1. General terms."
    )
    body, title, author = strip_gutenberg(text)
    assert (title, author) == ("Harbour Tales", "Ana Ruiz")
    assert "Gutenberg" not in body and body.startswith("Chapter 1")
    doc = parse_text(text)
    assert (doc.title, doc.author) == ("Harbour Tales", "Ana Ruiz")
    assert "General terms" not in " ".join(text for _, text in blocks(doc))


def test_text_without_gutenberg_markers_is_untouched():
    assert strip_gutenberg("Just a story.") == ("Just a story.", None, None)


def test_contents_pages_are_dropped():
    listed = "Book\n\nContents\n\n   I.  The Harbour\n   II. Night Crossing\n\nI. THE HARBOUR\n\nIt began."
    assert "Night Crossing" not in drop_contents(listed) and "I. THE HARBOUR" in drop_contents(listed)
    numbered = "The Harbour        3\nA Letter from the Hill   11\nNight Crossing .... 19\n\nIt began."
    assert drop_contents(numbered).strip() == "It began."
    two_lines = "Score  3\nAway  1\n\nIt began."  # fewer than three page-number lines: not a contents page
    assert drop_contents(two_lines) == two_lines


def test_a_byline_under_the_title_is_the_author_not_a_chapter():
    doc = parse_text(f"Harbour Tales\n\nby Ana Ruiz\n\n{LONG}")
    assert (doc.title, doc.author) == ("Harbour Tales", "Ana Ruiz")
    assert blocks(doc) == [("paragraph", LONG.strip())]


def test_bold_italic_markers_and_rtf_leftovers_are_never_read():
    assert clean_inline("***The Adventures*** is a book") == "The Adventures is a book"
    assert clean_title("}Avengers Doomsday") == "Avengers Doomsday"

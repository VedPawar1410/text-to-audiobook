import pytest

from app.ingest import IngestError
from app.ingest.pdf import text_from_pdf
from app.structure import parse_text
from tests.pdf_factory import make_pdf, page_of_lines


def test_prose_pdf_keeps_paragraphs_and_cleans_page_furniture():
    page = page_of_lines([
        "Chapter One",
        "",
        "The citadel stood at the end of time. Its halls were",
        "silent and its windows dark.",
        "",
        "Only one light burned in the high-",
        "est tower. Inside, a man waited.",
        "",
        "7",
    ])  # fmt: skip

    text, title, _ = text_from_pdf(make_pdf([page], title="The Citadel"))
    doc = parse_text(text)

    assert title == "The Citadel"
    assert "highest tower" in text  # de-hyphenated
    assert "\n7" not in text  # page number dropped
    assert [b.text for b in doc.sections[0].blocks] == [
        "Chapter One",
        "The citadel stood at the end of time. Its halls were silent and its windows dark.",
        "Only one light burned in the highest tower. Inside, a man waited.",
    ]


def test_repeated_running_header_is_removed():
    pages = [
        page_of_lines(["THE CITADEL - DRAFT", "", f"Paragraph on page {n}.", "", f"Page {n} of 3"])
        for n in (1, 2, 3)
    ]

    text, _, _ = text_from_pdf(make_pdf(pages))

    assert "DRAFT" not in text and "of 3" not in text
    assert "Paragraph on page 2." in text


def test_screenplay_pdf_is_parsed_as_screenplay():
    page = page_of_lines([
        "INT. CITADEL - NIGHT",
        "",
        "A vast hall. Candles flicker.",
        "",
        (22, "KANG"),
        (15, "(quietly)"),
        (10, "Every timeline ends."),
        (10, "Even yours."),
        "",
        "He turns away.",
        "",
        "EXT. VOID - CONTINUOUS",
    ])  # fmt: skip

    text, _, _ = text_from_pdf(make_pdf([page]))
    doc = parse_text(text)

    assert doc.format == "screenplay"
    dialogue = [b for s in doc.sections for b in s.blocks if b.kind == "dialogue"]
    assert [(b.speaker, b.direction, b.text) for b in dialogue] == [
        ("KANG", "quietly", "Every timeline ends. Even yours.")
    ]


def test_pdf_without_text_is_rejected():
    with pytest.raises(IngestError, match="Scanned"):
        text_from_pdf(make_pdf([[]]))


def test_non_pdf_bytes_are_rejected():
    with pytest.raises(IngestError, match="readable PDF"):
        text_from_pdf(b"definitely not a pdf")


PARAGRAPHS = [
    ("The lamp turned slowly above the harbour, throwing its long beam across the black water while "
     "the keeper wrote the name of every passing ship into the green ledger on his desk."),
    ("Nobody in the village remembered who had built the tower, and nobody asked any more, because the "
     "answer had changed so many times that it no longer seemed to matter to anyone at all."),
    ("Morning came grey and cold, and with it a boat that nobody had seen leave, tied to the end of the "
     "quay with its deck still wet and its small cabin door swinging open in the wind."),
    ("She walked the length of it twice before she let herself climb aboard and look inside, and what "
     "she found there was a coat on a hook, a compass, and a folded page from the ledger."),
]


def _typeset(paragraphs: list[str], indent: bool) -> list[str | tuple[int, str]]:
    import textwrap

    lines: list[str | tuple[int, str]] = []
    for paragraph in paragraphs:
        wrapped = textwrap.wrap(paragraph, 60)
        lines += [(4, wrapped[0]) if indent else wrapped[0], *wrapped[1:]]
    return lines


def test_a_typeset_book_loses_its_running_headers_and_keeps_indented_paragraphs():
    one, two, three, four = (_typeset([p], indent=True) for p in PARAGRAPHS)
    pages = [
        page_of_lines(["HARBOUR TALES", "", (8, "by Ana Ruiz")]),  # title page
        page_of_lines(["HARBOUR TALES", "", "", "CHAPTER ONE: THE QUAY", "", *one, two[0]]),
        page_of_lines(["THE QUAY", "", "", *two[1:], *three]),  # alternating header; paragraph 2 runs on
        page_of_lines(["CHAPTER TWO", "", *four]),  # a chapter opening has no running header
        page_of_lines(["THE LEDGER", "", "", (4, "It was the last entry he would ever make in it, and he knew it.")]),
    ]

    text, title, _ = text_from_pdf(make_pdf(pages, title="Microsoft Word - tales_v2.docx"))
    doc = parse_text(text, title=title)

    blocks = [b for s in doc.sections for b in s.blocks]
    assert [b.text for b in blocks if b.kind == "heading"] == ["CHAPTER ONE: THE QUAY", "CHAPTER TWO"]
    assert [b.text for b in blocks if b.kind == "paragraph"] == [
        *PARAGRAPHS, "It was the last entry he would ever make in it, and he knew it."
    ]  # the header lines are gone and the paragraph split across pages 2-3 is whole again
    assert title == "HARBOUR TALES"  # the title page, not the Word file name


def test_a_book_without_indents_breaks_paragraphs_at_short_last_lines():
    # Known limit: with no indents and no blank lines, a paragraph whose last line is nearly
    # full width can't be told from a line inside a paragraph, so only short last lines count.
    paragraphs = [
        ["The lamp turned slowly above the harbour, throwing its long", "beam across the black water while",
         "the keeper wrote."],
        ["Nobody in the village remembered who had built the tower,", "and nobody asked any more, because",
         "it no longer mattered."],
        ["Morning came grey and cold, and with it a boat that nobody", "had seen leave, tied to the end of",
         "the quay."],
        ["She walked the length of it twice before she climbed aboard", "and looked inside, and found a coat,",
         "and a compass."],
    ]  # fmt: skip
    pages = [page_of_lines([line for paragraph in paragraphs for line in paragraph])]

    text, _, _ = text_from_pdf(make_pdf(pages))

    assert [b.text for b in parse_text(text).sections[0].blocks] == [" ".join(p) for p in paragraphs]


def test_a_good_metadata_title_is_kept_over_the_title_page():
    pages = [page_of_lines(["COVER TEXT", "", "Hello there."])]
    _, title, _ = text_from_pdf(make_pdf(pages, title="The Citadel"))
    assert title == "The Citadel"


def test_author_comes_from_the_pdf_metadata():
    _, title, author = text_from_pdf(make_pdf([page_of_lines(["Hello there."])], title="Report", author="Ada Byron"))

    assert (title, author) == ("Report", "Ada Byron")

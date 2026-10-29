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

    text, title = text_from_pdf(make_pdf([page], title="The Citadel"))
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

    text, _ = text_from_pdf(make_pdf(pages))

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

    text, _ = text_from_pdf(make_pdf([page]))
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

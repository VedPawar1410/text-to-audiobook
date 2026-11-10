"""Render the synthetic book into the messy formats people actually import, with the truth.

Each case mirrors a real input measured in the Nov 2026 revive: a paste from X with single
line breaks, a Project Gutenberg file, a typeset book PDF, a web article, and an "unusual"
book whose chapter titles are bare words.
"""

import textwrap
from dataclasses import dataclass, field

from structure_eval.corpus import AUTHOR, TITLE, Chapter, build_book
from tests.pdf_factory import make_pdf

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
ORDINAL = ["One", "Two", "Three", "Four", "Five", "Six"]


@dataclass
class Truth:
    title: str | None
    author: str | None
    headings: list[str]  # every chapter heading and sub-heading, as rendered
    paragraphs: list[str]  # every story paragraph, unwrapped to one line
    junk: list[str] = field(default_factory=list)  # text that must never be spoken


@dataclass
class Case:
    name: str
    description: str
    kind: str  # "text" (paste or .txt/.md upload) or "pdf"
    payload: str | bytes
    truth: Truth
    title_hint: str | None = None  # what the importer passes along: file name, page metadata
    author_hint: str | None = None
    count_stray_numbers: bool = False  # the book has no digits, so any bare number is a leak


def _paragraphs(chapters: list[Chapter]) -> list[str]:
    return [text for chapter in chapters for kind, text in chapter.items if kind == "p"]


def paste_blank_lines(chapters: list[Chapter]) -> Case:
    """The easy control: blank lines everywhere and 'Chapter One: ...' headings."""
    out, headings = [TITLE, "", f"by {AUTHOR}", ""], []
    for number, chapter in enumerate(chapters):
        headings.append(f"Chapter {ORDINAL[number]}: {chapter.name}")
        out += [headings[-1], ""]
        for kind, text in chapter.items:
            if kind == "sub":
                headings.append(text)
            out += [text, ""]
    truth = Truth(TITLE, AUTHOR, headings, _paragraphs(chapters))
    return Case("paste_blank_lines", "Paste with blank lines and 'Chapter One:' headings (control)", "text", "\n".join(out), truth)


def paste_single_newlines(chapters: list[Chapter]) -> Case:
    """Copied from X or a web page: one line break between everything, headings glued to text."""
    acts = ["Act One:", "Act Two:", "Act Three", "Post-Credits Scene:"]
    out, headings = [f"{TITLE} full story", ""], []
    for number, chapter in enumerate(chapters):
        headings.append(acts[number])
        out.append(acts[number])
        for kind, text in chapter.items:
            if kind == "sub":
                headings.append(f"{text}:")
            out.append(headings[-1] if kind == "sub" else text)
    truth = Truth(f"{TITLE} full story", None, headings, _paragraphs(chapters))
    return Case("paste_single_newlines", "X-style paste: single line breaks, 'Act One:' glued to its text", "text", "\n".join(out), truth)


LICENCE = [
    "This ebook is for the use of anyone anywhere at no cost and with almost no restrictions",
    "whatsoever. You may copy it, give it away or re-use it under the terms of the licence",
    "included with this ebook or online.",
]
END_LICENCE = [
    "Updated editions will replace the previous one, and the old editions will be renamed.",
    "",
    "Creating the works from print editions not protected by copyright law means that no one",
    "owns a copyright in these works, so the foundation can copy and distribute it freely.",
    "",
    "Section one. General terms of use and redistributing this electronic work.",
]


def gutenberg_style(chapters: list[Chapter]) -> Case:
    """A Project Gutenberg plain-text file: licence header and footer, a contents page,
    Roman-numeral headings in capitals, lines hard-wrapped at 70 characters."""
    marker = f"THE PROJECT GUTENBERG EBOOK {TITLE.upper()}"
    out = [f"The Project Gutenberg eBook of {TITLE}", "", *LICENCE, "", f"Title: {TITLE}", "",
           f"Author: {AUTHOR}", "", f"*** START OF {marker} ***", "", "", "", TITLE, "", f"by {AUTHOR}", "", "", "Contents", ""]
    contents = [f"{ROMAN[n]}. {c.name}" for n, c in enumerate(chapters)]
    out += [f"   {ROMAN[n]}.{' ' * (6 - len(ROMAN[n]))}{c.name}" for n, c in enumerate(chapters)] + ["", "", ""]
    headings = []
    for number, chapter in enumerate(chapters):
        headings.append(f"{ROMAN[number]}. {chapter.name.upper()}")
        out += [headings[-1], "", ""]
        for kind, text in chapter.items:
            if kind == "sub":
                headings.append(text.upper())
                out += ["", headings[-1], "", ""]
            else:
                out += [*textwrap.wrap(text, 70), ""]
    out += ["", "", f"*** END OF {marker} ***", "", *END_LICENCE]
    junk = [*contents, "Project Gutenberg", "This ebook is for the use of anyone", "Updated editions will replace",
            "Section one. General terms"]
    truth = Truth(TITLE, AUTHOR, headings, _paragraphs(chapters), junk)
    return Case("gutenberg_style", "Gutenberg .txt: licence, contents page, 'I. THE HARBOUR', hard-wrapped", "text", "\n".join(out), truth)


def book_pdf(chapters: list[Chapter]) -> Case:
    """A typeset book: indented paragraphs with no blank lines, running headers that alternate
    between the book title and the chapter title, page numbers, a contents page."""
    width, top, bottom, lead = 64, 700, 90, 14
    pages: list[list[tuple[float, float, str]]] = []
    page: list[tuple[float, float, str]] = []
    y = top
    chapter_of_page: list[str] = []
    current = ""

    def new_page() -> None:
        nonlocal page, y
        if page:
            pages.append(page)
            chapter_of_page.append(current)
        page, y = [], top

    def emit(text: str, x: float = 72, gap_after: int = 0) -> None:
        nonlocal y
        if y < bottom:
            new_page()
        page.append((x, y, text))
        y -= lead * (1 + gap_after)

    emit(TITLE.upper(), 170, 1)
    emit(f"by {AUTHOR}", 220)
    new_page()
    emit("CONTENTS", 72, 1)
    for number, chapter in enumerate(chapters):
        emit(f"{chapter.name:48}{3 + number * 2:>4}")
    new_page()

    headings = []
    for number, chapter in enumerate(chapters):
        new_page()
        current = chapter.name.upper()
        headings.append(f"CHAPTER {ORDINAL[number].upper()}: {chapter.name.upper()}")
        emit(headings[-1], 72, 1)
        for kind, text in chapter.items:
            if kind == "sub":
                y -= lead
                headings.append(text)
                emit(text, 72, 1)
            else:
                for line in textwrap.wrap(text, width, initial_indent="    "):
                    emit(line)
    new_page()

    for number, lines in enumerate(pages[2:], start=2):  # furniture goes on after layout
        lines.insert(0, (200, 750, TITLE.upper() if number % 2 == 0 else chapter_of_page[number]))
        lines.append((300, 40, str(number + 1)))
    data = make_pdf(pages, title="Microsoft Word - ledger_final.docx", author=AUTHOR)
    junk = [TITLE.upper(), "CONTENTS", *[c.name.upper() for c in chapters]]
    truth = Truth(TITLE, AUTHOR, headings, _paragraphs(chapters), junk)
    return Case("book_pdf", "Typeset PDF: indented paragraphs, alternating running headers, page numbers",
                "pdf", data, truth, count_stray_numbers=True)


def web_markdown(chapters: list[Chapter]) -> Case:
    """What the URL importer hands over (trafilatura's markdown), with a reference list at the
    end and junk page metadata as the 'author'."""
    out, headings = [f"# {TITLE}", ""], []
    for chapter in chapters:
        headings.append(chapter.name)
        out += [f"## {chapter.name}", ""]
        for kind, text in chapter.items:
            if kind == "sub":
                headings.append(text)
                out += [f"### {text}", ""]
            else:
                out += [text, ""]
    references = ["Ellison, M. (2019). Lighthouses of the north coast. Harbour Press. p. 112.",
                  "Coastal Archive (2021). Ship registers, volume 4. Retrieved 3 March 2022."]
    links = ["Official site of the Lighthouse Society", "Keeper's Ledger at the Coastal Archive"]
    out += ["## References", "", *[f"- {r}" for r in references], "", "## External links", "", *[f"- {link}" for link in links]]
    truth = Truth(TITLE, None, headings, _paragraphs(chapters), [*references, *links])
    return Case("web_markdown", "Web article (URL import): reference list and junk metadata author", "text",
                "\n".join(out), truth, author_hint="Authority control databases National Library Other")


def unusual_headings(chapters: list[Chapter]) -> Case:
    """Chapter titles as bare words with no number or 'Chapter' (common in modern novels)."""
    out, headings = [TITLE, "", f"by {AUTHOR}", ""], []
    for chapter in chapters:
        headings.append(chapter.name)
        out += [chapter.name, ""]
        for kind, text in chapter.items:
            if kind == "sub":
                headings.append(text)
            out += [text, ""]
    truth = Truth(TITLE, AUTHOR, headings, _paragraphs(chapters))
    return Case("unusual_headings", "Bare-word chapter titles ('The Harbour'), next to one-line dialogue", "text", "\n".join(out), truth)


def all_cases() -> list[Case]:
    chapters = build_book()
    return [render(chapters) for render in (paste_blank_lines, paste_single_newlines, gutenberg_style,
                                             book_pdf, web_markdown, unusual_headings)]

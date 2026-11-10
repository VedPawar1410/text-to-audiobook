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


def _epub(documents: list[tuple[str, str, str]], title: str, author: str | None) -> bytes:
    """A minimal valid EPUB 3. documents: (file name, "nav" / "linear-no" / "", xhtml body)."""
    import io
    import zipfile
    from html import escape

    items, itemrefs = [], []
    for n, (name, role, _) in enumerate(documents):
        properties = ' properties="nav"' if role == "nav" else ""
        linear = ' linear="no"' if role == "linear-no" else ""
        items.append(f'<item id="d{n}" href="{name}" media-type="application/xhtml+xml"{properties}/>')
        itemrefs.append(f'<itemref idref="d{n}"{linear}/>')
    creator = f"<dc:creator>{escape(author)}</dc:creator>" if author else ""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")  # first and uncompressed
        archive.writestr("META-INF/container.xml", (
            '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
            "</rootfiles></container>"
        ))  # fmt: skip
        archive.writestr("OEBPS/content.opf", (
            '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">ledger</dc:identifier>'
            f"<dc:title>{escape(title)}</dc:title>{creator}<dc:language>en</dc:language></metadata>"
            f"<manifest>{''.join(items)}</manifest><spine>{''.join(itemrefs)}</spine></package>"
        ))  # fmt: skip
        for name, _, body in documents:
            archive.writestr(f"OEBPS/{name}", (
                '<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" '
                f'xmlns:epub="http://www.idpf.org/2007/ops"><head><title>x</title></head><body>{body}</body></html>'
            ))  # fmt: skip
    return buffer.getvalue()


def publisher_epub(chapters: list[Chapter]) -> Case:
    """A well-made EPUB: real <h2>/<h3> headings, plus a cover, navigation, a copyright page,
    page-break markers carrying page numbers, and a footnote: none of which may be read."""
    from html import escape

    links = "".join(f'<li><a href="c{n}.xhtml">{escape(c.name)}</a></li>' for n, c in enumerate(chapters))
    documents = [
        ("cover.xhtml", "linear-no", "<p>Cover image</p>"),
        ("nav.xhtml", "nav", f'<nav epub:type="toc"><h1>Contents</h1><ol>{links}</ol></nav>'),
        ("title.xhtml", "", f"<h1>{escape(TITLE)}</h1><p>by {escape(AUTHOR)}</p>"),
        ("copyright.xhtml", "", ('<section epub:type="copyright-page"><p>Copyright Mara Ellison. '
                                 "All rights reserved. No part of this book may be reproduced.</p></section>")),
    ]  # fmt: skip
    headings, page = [], 4
    for number, chapter in enumerate(chapters):
        headings.append(chapter.name)
        body = [f'<section epub:type="chapter"><h2>{escape(chapter.name)}</h2>']
        for index, (kind, text) in enumerate(chapter.items):
            if kind == "sub":
                headings.append(text)
                body.append(f"<h3>{escape(text)}</h3>")
            elif index % 5 == 4:  # a page break in mid-paragraph, as print-replica EPUBs have
                page += 1
                cut = text.index(" ", len(text) // 2)
                marker = f'<span epub:type="pagebreak" id="p{page}">{page}</span>'
                body.append(f"<p>{escape(text[:cut])}{marker}{escape(text[cut:])}</p>")
            else:
                body.append(f"<p>{escape(text)}</p>")
        if number == 0:
            body.append('<aside epub:type="footnote"><p>The harbour was rebuilt twice in living memory.</p></aside>')
        documents.append((f"c{number}.xhtml", "", "".join(body) + "</section>"))
    junk = ["Cover image", "All rights reserved", "rebuilt twice in living memory", "Contents"]
    truth = Truth(TITLE, AUTHOR, headings, _paragraphs(chapters), junk)
    return Case("publisher_epub", "EPUB with real headings, nav, copyright page, page-break numbers, a footnote",
                "epub", _epub(documents, TITLE, AUTHOR), truth, count_stray_numbers=True)


def calibre_epub(chapters: list[Chapter]) -> Case:
    """What an online converter (CloudConvert, i.e. Calibre) makes from a text file: every line a
    <p class="calibre2">, no real headings, author "Unknown". The text rules must still work."""
    from html import escape

    acts = ["Act One:", "Act Two:", "Act Three", "Post-Credits Scene:"]
    paragraphs, headings = [f"{TITLE} full story"], []
    for number, chapter in enumerate(chapters):
        headings.append(acts[number])
        paragraphs.append(acts[number])
        for kind, text in chapter.items:
            if kind == "sub":
                headings.append(f"{text}:")
            paragraphs.append(f"{text}:" if kind == "sub" else text)
    body = "".join(f'<p class="calibre2">{escape(p)}</p>' for p in paragraphs)
    truth = Truth(f"{TITLE} full story", None, headings, _paragraphs(chapters))
    data = _epub([("index_split_000.html", "", body)], f"{TITLE} full story", "Unknown")
    return Case("calibre_epub", "Converter-made EPUB from a text file: no headings, author 'Unknown'", "epub", data, truth)


def all_cases() -> list[Case]:
    chapters = build_book()
    renderers = (paste_blank_lines, paste_single_newlines, gutenberg_style, book_pdf, web_markdown,
                 unusual_headings, publisher_epub, calibre_epub)  # fmt: skip
    return [render(chapters) for render in renderers]

"""PDF → plain text.

pypdf's "layout" mode keeps blank lines between paragraphs and screenplay
indentation, both lost in its default mode (checked in PR 4), so the same text
parser handles PDFs. Here we remove page furniture (page numbers, running
headers/footers, words hyphenated across lines) and turn a typeset book's
paragraph indents into blank lines, which is what the text parser understands.
"""

import io
import re
from collections import Counter

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingest import IngestError
from app.structure.prose import heading_strength
from app.structure.screenplay import looks_like_screenplay

PAGE_NUMBER = re.compile(r"^\s*(?:page\s+)?\d{1,4}(?:\s*(?:of|/)\s*\d{1,4})?\.?\s*$", re.IGNORECASE)
CONTINUED = re.compile(r"^\s*(?:\((?:MORE|CONTINUED)\)|CONTINUED:?)\s*$", re.IGNORECASE)
SENTENCE_END = (".", "!", "?", ",", ";", '"', "'", "”", "’", ")", "…")
PARAGRAPH_END = (".", "!", "?", '"', "”", "’", ")", "…")
# A title written by the authoring app, not the author: "Microsoft Word - x.docx", "my_book_final"
GENERATED_TITLE = re.compile(r"^(?:microsoft|untitled)|\.(?:docx?|pdf|pages|odt|rtf|txt)$|^\S*_\S*$", re.IGNORECASE)

SLOT_SHARE = 0.6  # a header/footer "slot" is filled on at least this share of pages
SHORT_LINE = 70  # running headers, titles and headings are shorter than this


def _edge_key(line: str) -> str | None:
    """Normalise a header/footer line so "Page 3" and "Page 4" compare equal."""
    stripped = line.strip()
    return re.sub(r"\d+", "#", stripped.lower()) if stripped else None


def _repeated_edge_lines(pages: list[list[str]]) -> set[str]:
    """Lines that appear at the top or bottom of at least half the pages."""
    if len(pages) < 3:
        return set()
    counts: Counter[str] = Counter()
    for lines in pages:
        nonempty = [line for line in lines if line.strip()]
        # On a short page, "top 2 + bottom 2" would cover the body text too
        depth = 2 if len(nonempty) > 4 else 1
        counts.update({_edge_key(line) for line in nonempty[:depth] + nonempty[-depth:]})
    threshold = max(3, len(pages) * 0.5)
    return {key for key, count in counts.items() if key and count >= threshold}


def _slot_lines(pages: list[list[str]], top: bool) -> set[tuple[int, int]]:
    """A running header (or footer) slot: on most pages the first (last) line is short, isn't a
    sentence, and is set apart from the text by a blank line. This also catches headers that
    change with the chapter, which never repeat often enough for _repeated_edge_lines."""
    found: list[tuple[int, int]] = []
    for page, lines in enumerate(pages):
        filled = [i for i, line in enumerate(lines) if line.strip()]
        if len(filled) < 2:
            continue
        i = filled[0] if top else filled[-1]
        neighbour = lines[i + 1] if top else lines[i - 1]
        line = lines[i].strip()
        if not neighbour.strip() and len(line) <= SHORT_LINE and not line.endswith(SENTENCE_END):
            found.append((page, i))
    if len(pages) < 3 or len(found) < SLOT_SHARE * len(pages):
        return set()
    # A chapter-opening page usually has no running header: its first line is the chapter
    # heading. Keep a one-off "CHAPTER ONE" / "I. THE HARBOUR"; repeated text is furniture.
    keys = Counter(_edge_key(pages[p][i]) for p, i in found)
    return {
        (p, i) for p, i in found
        if not (keys[_edge_key(pages[p][i])] == 1 and heading_strength(pages[p][i].strip(), alone=True) == 1)
    }  # fmt: skip


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _mark_paragraphs(lines: list[str]) -> list[str]:
    """Typeset books show a new paragraph by an indent (or a short last line), not a blank
    line. Insert the blank line the text parser expects."""
    body = [line for line in lines if line.strip()]
    if len(body) < 10:
        return lines
    margins = Counter(_indent(line) for line in body)
    base = margins.most_common(1)[0][0]
    indented = sum(count for margin, count in margins.items() if margin >= base + 2)
    marked: list[str] = []
    if indented >= 0.03 * len(body):  # the book indents its paragraphs
        for line in lines:
            if line.strip() and _indent(line) >= base + 2 and marked and marked[-1].strip():
                marked.append("")
            marked.append(line)
        return marked
    widths = sorted(len(line.strip()) for line in body)
    typical = widths[int(len(widths) * 0.8)]  # a full line's width
    for line in lines:
        marked.append(line)
        if line.strip().endswith(PARAGRAPH_END) and len(line.strip()) < 0.75 * typical:
            marked.append("")
    return marked


def clean_pdf_pages(pages: list[str]) -> str:
    page_lines = [page.split("\n") for page in pages]
    repeated = _repeated_edge_lines(page_lines)
    slots = _slot_lines(page_lines, top=True) | _slot_lines(page_lines, top=False)

    cleaned_pages: list[list[str]] = []
    for p, lines in enumerate(page_lines):
        kept = []
        for i, line in enumerate(lines):
            if (p, i) in slots or PAGE_NUMBER.match(line) or CONTINUED.match(line) or _edge_key(line) in repeated:
                continue
            kept.append(re.sub(r"(?<=\S) {2,}(?=\S)", " ", line.rstrip()))
        while kept and not kept[0].strip():
            kept.pop(0)
        while kept and not kept[-1].strip():
            kept.pop()
        cleaned_pages.append(kept)

    # Pages join with a plain newline, so a paragraph that runs onto the next page stays whole.
    # A heading at the top of a page keeps a blank line before it.
    lines: list[str] = []
    for kept in cleaned_pages:
        if kept and lines and heading_strength(kept[0].strip(), alone=True) is not None:
            lines.append("")
        lines += kept

    text = "\n".join(lines)
    if not looks_like_screenplay(text):  # a screenplay's indents mean dialogue, not paragraphs
        text = "\n".join(_mark_paragraphs(lines))
    return re.sub(r"(?<=[a-z])-\n\s*(?=[a-z])", "", text)  # "high-\nest" -> "highest"


def _title_page_line(pages: list[str]) -> str | None:
    """The first line of the first page, if it reads like a title (often also the running header)."""
    first = next((line.strip() for line in (pages[0].split("\n") if pages else []) if line.strip()), "")
    if not first or len(first) > 80 or first.endswith(SENTENCE_END) or PAGE_NUMBER.match(first):
        return None
    return first


def text_from_pdf(data: bytes) -> tuple[str, str | None, str | None]:
    """Return (text, title, author). Title and author come from the PDF's metadata; a title the
    authoring app made up ("Microsoft Word - x.docx") gives way to the title page."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise IngestError("This PDF is password-protected.")
        pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    except PdfReadError as error:
        raise IngestError("This file isn't a readable PDF.") from error

    if not any(page.strip() for page in pages):
        raise IngestError("No text found in this PDF. Scanned (image-only) PDFs aren't supported yet.")

    metadata = reader.metadata
    title = (metadata.title or "").strip() if metadata else ""
    author = (metadata.author or "").strip() if metadata else ""
    if not title or GENERATED_TITLE.search(title):
        title = _title_page_line(pages) or title
    return clean_pdf_pages(pages), title or None, author or None

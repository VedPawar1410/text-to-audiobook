"""PDF → plain text.

pypdf's "layout" mode keeps blank lines between paragraphs and screenplay
indentation, both lost in its default mode (checked in PR 4), so the same text
parser handles PDFs. Here we only remove page furniture: page numbers, repeated
headers/footers, and words hyphenated across lines.
"""

import io
import re
from collections import Counter

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingest import IngestError

PAGE_NUMBER = re.compile(r"^\s*(?:page\s+)?\d{1,4}(?:\s*(?:of|/)\s*\d{1,4})?\.?\s*$", re.IGNORECASE)
CONTINUED = re.compile(r"^\s*(?:\((?:MORE|CONTINUED)\)|CONTINUED:?)\s*$", re.IGNORECASE)


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


def clean_pdf_pages(pages: list[str]) -> str:
    page_lines = [page.split("\n") for page in pages]
    repeated = _repeated_edge_lines(page_lines)

    kept: list[str] = []
    for lines in page_lines:
        for line in lines:
            if PAGE_NUMBER.match(line) or CONTINUED.match(line) or _edge_key(line) in repeated:
                continue
            kept.append(re.sub(r"(?<=\S) {2,}(?=\S)", " ", line.rstrip()))
        # Pages join with a plain newline: a paragraph that runs onto the next page
        # stays whole (losing one paragraph break is better than splitting a sentence).

    text = "\n".join(kept)
    return re.sub(r"(?<=[a-z])-\n\s*(?=[a-z])", "", text)  # "high-\nest" -> "highest"


def text_from_pdf(data: bytes) -> tuple[str, str | None]:
    """Return (text, title from the PDF's metadata, if any)."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise IngestError("This PDF is password-protected.")
        pages = [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]
    except PdfReadError as error:
        raise IngestError("This file isn't a readable PDF.") from error

    if not any(page.strip() for page in pages):
        raise IngestError("No text found in this PDF. Scanned (image-only) PDFs aren't supported yet.")

    title = (reader.metadata.title or "").strip() if reader.metadata else ""
    return clean_pdf_pages(pages), title or None

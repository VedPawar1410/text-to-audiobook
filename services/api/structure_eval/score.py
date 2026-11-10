"""Run a case through the real import path and score the structure it produces.

Metrics (all outcome-level, so they don't care how the parser works inside):
- paragraphs: share of the book's paragraphs that come out exactly right (one block each,
  nothing glued on, nothing split off). Merged or split paragraphs both fail.
- headings: chapter/sub-headings found, plus "extra" blocks wrongly made headings.
- junk: things read aloud that never should be (licence, contents, running headers, references,
  page numbers). Searched in non-heading text only; a junk line turned heading counts as extra.
- words lost: story words missing from the output. Deleting real text is the worst failure.
"""

import re
from collections import Counter
from dataclasses import dataclass

from app.ingest.pdf import text_from_pdf
from app.structure import parse_text
from app.structure.models import ParsedDocument
from structure_eval.cases import Case

HEADING_KINDS = ("heading", "scene_heading")


def import_case(case: Case) -> ParsedDocument:
    """The same calls the /ingest routes make."""
    if case.kind == "pdf":
        text, title, author = text_from_pdf(case.payload)
        return parse_text(text, title=title or case.title_hint, author=author)
    return parse_text(case.payload, title=case.title_hint, author=case.author_hint)


def _norm(text: str) -> str:
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip()


def _heading_key(text: str) -> str:
    return _norm(text).lower().rstrip(":.")


def _words(text: str) -> Counter:
    return Counter(re.findall(r"[a-z']+", _norm(text).lower()))


@dataclass
class Score:
    case: str
    description: str
    paragraphs_exact: int
    paragraphs_total: int
    headings_found: int
    headings_total: int
    headings_extra: int
    junk_spoken: int
    words_lost: int
    title_ok: bool
    author_ok: bool

    @property
    def paragraph_pct(self) -> float:
        return 100 * self.paragraphs_exact / max(1, self.paragraphs_total)


def score_document(case: Case, document: ParsedDocument) -> Score:
    truth = case.truth
    blocks = [b for s in document.sections for b in s.blocks if b.kind != "scene_break"]
    headings = [_heading_key(b.text) for b in blocks if b.kind in HEADING_KINDS]
    body = [_norm(b.text) for b in blocks if b.kind not in HEADING_KINDS]

    body_set = set(body)
    exact = sum(_norm(p) in body_set for p in truth.paragraphs)

    expected = [_heading_key(h) for h in truth.headings]
    remaining = Counter(headings)
    found = 0
    for key in expected:
        if remaining[key] > 0:
            remaining[key] -= 1
            found += 1
    extra = sum(remaining.values())

    body_text = " \n ".join(body)
    junk = sum(body_text.count(_norm(j)) for j in truth.junk)
    if case.count_stray_numbers:
        junk += len(re.findall(r"(?<![\w'])\d{1,4}(?![\w'])", body_text))

    wanted = _words(" ".join(truth.paragraphs + truth.headings))
    spoken = _words(" ".join(b.text for b in blocks))
    lost = sum((wanted - spoken).values())

    return Score(
        case=case.name,
        description=case.description,
        paragraphs_exact=exact,
        paragraphs_total=len(truth.paragraphs),
        headings_found=found,
        headings_total=len(expected),
        headings_extra=extra,
        junk_spoken=junk,
        words_lost=lost,
        title_ok=_norm(document.title or "") == _norm(truth.title or ""),
        author_ok=(document.author or None) == truth.author,
    )


def score_case(case: Case) -> Score:
    return score_document(case, import_case(case))

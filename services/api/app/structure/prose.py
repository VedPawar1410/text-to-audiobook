"""Parse prose and markdown: headings, chapters, paragraphs, lists, quotes, scene breaks."""

import re

from app.structure.models import Block, Section

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
CHAPTER = re.compile(
    r"^(?:chapter|part|book|act|scene|prologue|epilogue|interlude|post-credits)\b.{0,60}$", re.IGNORECASE
)
ROMAN_HEADING = re.compile(r"^[IVXLC]+\.(?:\s+(\S.{0,70}))?$")  # "I." or "I. A SCANDAL IN BOHEMIA"
SCENE_BREAK = re.compile(r"^(?:[*#~=-]\s*){3,}$")  # ***, * * *, ---, ###
LIST_ITEM = re.compile(r"^(?:[-*•]|\d{1,3}[.)])\s+(.*)$")
QUOTE = re.compile(r"^>\s?(.*)$")

# A line this long or longer is a whole paragraph, not a hard-wrapped line (books wrap at ~60-80)
WRAP_WIDTH = 100
SENTENCE_END = (".", "!", "?", ",", ";", '"', "'", "”", "’", ")", "…")
SMALL_WORDS = {"a", "an", "the", "and", "or", "but", "nor", "of", "in", "on", "at", "to", "for", "from", "by",
               "with", "as", "into", "over", "upon", "vs"}  # fmt: skip

# Heading strength. A STRONG heading ("Chapter 3", "I. THE HARBOUR", "## Title") always starts a
# chapter. A WEAK one (a short Title Case or CAPS line on its own) starts a chapter only when the
# text has no strong headings at all; otherwise it's a sub-heading inside the chapter.
STRONG, WEAK = 1, 2


def _title_case(text: str) -> bool:
    words = re.findall(r"[^\W\d_][\w'’-]*", text)
    if not words or not words[0][0].isupper():
        return False
    return all(w[0].isupper() or w.lower() in SMALL_WORDS for w in words[1:])


def _caps(text: str) -> bool:
    return sum(c.isalpha() for c in text) >= 2 and text == text.upper()


def heading_strength(line: str, alone: bool) -> int | None:
    """Is this line a heading? alone: it stands by itself, not glued to the text below it."""
    words = line.split()
    if len(line) > 80 or len(words) > 10:
        return None
    if match := ROMAN_HEADING.match(line):
        rest = match[1]
        if rest is None:
            return WEAK  # a bare "I." / "II." part marker
        return STRONG if not rest.endswith(SENTENCE_END) and (_caps(rest) or _title_case(rest)) else None
    # Glued to text, "Part of the reason was that" must not count: ask for a heading's shape
    heading_shape = alone or line.endswith(":") or _caps(line) or _title_case(line)
    if CHAPTER.match(line) and not line.endswith((".", "!", "?")) and heading_shape:
        return STRONG
    if line.endswith(SENTENCE_END):
        return None
    if line.endswith(":"):  # "Act One:", "The First Night:" (but not "What he remembered:")
        return WEAK if len(words) <= 6 and (_title_case(line[:-1]) or _caps(line)) else None
    if alone and len(words) <= 8 and (_caps(line) or _title_case(line)):
        return WEAK
    return None


def clean_inline(text: str) -> str:
    """Strip inline markdown so the voice never reads asterisks or link URLs."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # [label](url) -> label
    text = re.sub(r"(\*\*\*|___)(\S(?:.*?\S)?)\1", r"\2", text)  # ***bold italic***
    text = re.sub(r"(\*\*|__|\*|_|`)(\S(?:.*?\S)?)\1", r"\2", text)  # **b**, *i*, `code`
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>])", r"\1", text)  # escapes: "\[" -> "["
    return re.sub(r"\s+", " ", text).strip()


def _chunks(text: str):
    """Blank-line-separated groups of lines; a markdown heading always stands alone."""
    chunk: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            if chunk:
                yield chunk
            chunk = []
        elif HEADING.match(stripped):
            if chunk:
                yield chunk
            chunk = []
            yield [stripped]
        else:
            chunk.append(stripped)
    if chunk:
        yield chunk


def _list_items(lines: list[str]) -> list[str]:
    """Group lines into items: a marker starts an item, other lines continue it."""
    items: list[list[str]] = []
    for line in lines:
        match = LIST_ITEM.match(line)
        if match:
            items.append([match[1]])
        else:
            items[-1].append(line)
    return [" ".join(item) for item in items]


def _is_hard_wrapped(lines: list[str]) -> bool:
    """Short lines that continue each other (a book or Gutenberg file) get joined; long ones
    (a paste from X or a web page, one paragraph per line) each stay a paragraph."""
    return len(lines) == 1 or max(len(line) for line in lines[:-1]) <= WRAP_WIDTH


def _items(text: str):
    """First pass: (kind, text, heading strength) for every chunk, in order."""

    def chunk(lines: list[str], alone: bool):
        first = lines[0]
        single = len(lines) == 1
        if single and SCENE_BREAK.match(first):
            yield "scene_break", "", None
        elif single and (match := HEADING.match(first)):
            yield "markdown_heading", match[2], len(match[1])
        elif (strength := heading_strength(first, alone=alone and single)) is not None:
            yield "heading", first, strength
            if not single:  # a heading glued to its text: "Act One:\nWe open on..."
                yield from chunk(lines[1:], alone=alone)
        elif LIST_ITEM.match(first):
            for item in _list_items(lines):
                yield "list_item", item, None
        elif all(QUOTE.match(line) for line in lines):
            yield "quote", " ".join(QUOTE.match(line)[1] for line in lines), None
        elif _is_hard_wrapped(lines):
            yield "paragraph", " ".join(lines), None
        else:
            for line in lines:  # one paragraph per line, and a short line among them may be a heading
                yield from chunk([line], alone=True)

    for lines in _chunks(text):
        yield from chunk(lines, alone=True)


def parse_prose(text: str) -> tuple[str | None, list[Section]]:
    """Return (title from a leading '# Title', sections)."""
    items = list(_items(text))
    title: str | None = None
    if items and items[0][0] == "markdown_heading" and items[0][2] == 1:
        title = clean_inline(items.pop(0)[1])
    has_strong = any(
        (kind == "heading" and strength == STRONG) or (kind == "markdown_heading" and strength <= 2)
        for kind, _, strength in items
    )
    # Explicit structure beats guessing: when the text has real (markdown) headings, as every
    # EPUB and web article does, a short Title Case line is a paragraph, not a heading.
    has_markdown = any(kind == "markdown_heading" for kind, _, _ in items)

    sections = [Section()]

    def start_section(name: str) -> None:
        if sections[-1].blocks:
            sections.append(Section())
        sections[-1].title = clean_inline(name)
        sections[-1].blocks.append(Block(kind="heading", text=clean_inline(name)))

    def add(kind, text: str) -> None:
        text = clean_inline(text)
        if text:
            sections[-1].blocks.append(Block(kind=kind, text=text))

    for kind, value, strength in items:
        if kind == "scene_break":
            sections[-1].blocks.append(Block(kind="scene_break", text=""))
        elif kind == "heading" and strength == WEAK and has_markdown:
            add("paragraph", value)
        elif kind in ("markdown_heading", "heading"):
            if kind == "markdown_heading":
                starts_chapter = strength <= 2  # "#"/"##" are chapters, "###" and deeper sub-headings
            else:
                starts_chapter = strength == STRONG or not has_strong
            if starts_chapter:
                start_section(value)
            else:
                add("heading", value)
        else:
            add(kind, value)

    return title, [s for s in sections if s.blocks]

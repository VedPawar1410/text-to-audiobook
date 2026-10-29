"""Parse prose and markdown: headings, chapters, paragraphs, lists, quotes, scene breaks."""

import re

from app.structure.models import Block, Section

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
CHAPTER = re.compile(
    r"^(?:chapter|part|book|act|scene|prologue|epilogue|interlude)\b.{0,60}$", re.IGNORECASE
)
SCENE_BREAK = re.compile(r"^(?:[*#~=-]\s*){3,}$")  # ***, * * *, ---, ###
LIST_ITEM = re.compile(r"^(?:[-*•]|\d{1,3}[.)])\s+(.*)$")
QUOTE = re.compile(r"^>\s?(.*)$")


def clean_inline(text: str) -> str:
    """Strip inline markdown so the voice never reads asterisks or link URLs."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # [label](url) -> label
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


def parse_prose(text: str) -> tuple[str | None, list[Section]]:
    """Return (title from a leading '# Title', sections)."""
    title: str | None = None
    sections = [Section()]

    def start_section(name: str) -> None:
        if sections[-1].blocks:
            sections.append(Section())
        sections[-1].title = name
        sections[-1].blocks.append(Block(kind="heading", text=clean_inline(name)))

    def add(kind, text: str) -> None:
        text = clean_inline(text)
        if text:
            sections[-1].blocks.append(Block(kind=kind, text=text))

    for lines in _chunks(text):
        first = lines[0]
        single = len(lines) == 1

        if single and SCENE_BREAK.match(first):
            sections[-1].blocks.append(Block(kind="scene_break", text=""))
        elif single and (match := HEADING.match(first)):
            level, heading = len(match[1]), match[2]
            nothing_yet = not any(s.blocks for s in sections)
            if level == 1 and title is None and nothing_yet:
                title = clean_inline(heading)
            elif level <= 2:
                start_section(heading)
            else:
                add("heading", heading)
        elif single and CHAPTER.match(first) and not first.endswith((".", "!", "?")):
            start_section(first)
        elif LIST_ITEM.match(first):
            for item in _list_items(lines):
                add("list_item", item)
        elif all(QUOTE.match(line) for line in lines):
            add("quote", " ".join(QUOTE.match(line)[1] for line in lines))
        else:
            add("paragraph", " ".join(lines))  # also unwraps hard-wrapped lines

    return title, [s for s in sections if s.blocks]

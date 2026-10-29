"""Text → ParsedDocument. Every input (paste, file, PDF, URL) ends up here as plain text.

This step is deterministic (regex + a sentence splitter): free, instant and predictable.
The AI director (next stage) only has to add meaning, not find the structure.
"""

import re

from app.structure.models import ParsedDocument, Section, Stats
from app.structure.prose import CHAPTER, parse_prose
from app.structure.screenplay import SLUGLINE, TRANSITION, looks_like_screenplay, parse_screenplay
from app.structure.sentences import split_sentences

WORDS_PER_MINUTE = 150  # typical audiobook narration pace


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("﻿", "").replace(" ", " ").replace("­", "").replace("\t", "    ")
    text = re.sub(r"[​-‍⁠]", "", text)  # zero-width characters
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip("\n")


def _leading_title(text: str) -> tuple[str | None, str]:
    """A short first line followed by a blank line is treated as the title."""
    first, _, rest = text.partition("\n\n")
    line = first.strip()
    if "\n" in first or not line or len(line) > 80 or not rest.strip():
        return None, text
    if match := re.match(r"^title\s*:\s*(.+)$", line, re.IGNORECASE):
        return match[1].strip(), rest
    if line.startswith("#") or line[-1] in ".!?,;" or line.endswith(" TO:"):
        return None, text
    if SLUGLINE.match(line) or TRANSITION.match(line) or CHAPTER.match(line):
        return None, text
    return line, rest


def _finalize(sections: list[Section]) -> None:
    for section in sections:
        for block in section.blocks:
            if block.kind == "scene_break":
                block.sentences = []
            elif block.kind in ("heading", "scene_heading", "transition"):
                block.sentences = [block.text]  # never split "INT. CITADEL" at the dot
            else:
                block.sentences = split_sentences(block.text)


def _stats(text: str, sections: list[Section]) -> Stats:
    blocks = [b for s in sections for b in s.blocks]
    words = sum(len(b.text.split()) for b in blocks)
    speakers = list(dict.fromkeys(b.speaker for b in blocks if b.speaker))
    return Stats(
        characters=len(text),
        words=words,
        sentences=sum(len(b.sentences) for b in blocks),
        speakers=speakers,
        estimated_minutes=round(words / WORDS_PER_MINUTE, 1),
    )


def parse_text(text: str, title: str | None = None) -> ParsedDocument:
    text = normalize(text)
    detected_title, body = _leading_title(text)

    if looks_like_screenplay(body):
        doc_format, sections = "screenplay", parse_screenplay(body)
    else:
        markdown_title, sections = parse_prose(body)
        detected_title = detected_title or markdown_title
        doc_format = "prose"

    _finalize(sections)
    return ParsedDocument(
        title=detected_title or title,
        format=doc_format,
        sections=sections,
        stats=_stats(text, sections),
    )

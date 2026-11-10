"""Text → ParsedDocument. Every input (paste, file, PDF, URL) ends up here as plain text.

This step is deterministic (regex + a sentence splitter): free, instant and predictable.
The AI director (next stage) only has to add meaning, not find the structure.
"""

import re

from app.structure.cleanup import drop_back_matter, drop_contents, strip_gutenberg
from app.structure.models import ParsedDocument, Section, Stats
from app.structure.prose import CHAPTER, ROMAN_HEADING, parse_prose
from app.structure.screenplay import SLUGLINE, TRANSITION, looks_like_screenplay, parse_screenplay
from app.structure.sentences import split_sentences

WORDS_PER_MINUTE = 150  # typical audiobook narration pace
# A chapter is also the unit that records, plays and gets a marker in the export. A long
# text with no headings would be one huge chapter, playable only once all of it is
# recorded, so it's cut into parts of about 10 minutes (Kokoro reads ~130 wpm).
PART_WORDS = 1500


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "").replace("\xa0", " ").replace("\xad", "").replace("\t", "    ")  # BOM, nbsp, soft hyphen
    text = re.sub("[\u200b-\u200d\u2060]", "", text)  # zero-width characters
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
    if SLUGLINE.match(line) or TRANSITION.match(line) or CHAPTER.match(line) or BYLINE.match(line) or ROMAN_HEADING.match(line):
        return None, text
    return line, rest


def _drop_leading_byline(body: str) -> str:
    """'by Arthur Conan Doyle' at the top becomes the author, not a 4-word first chapter."""
    first, _, rest = body.partition("\n\n")
    if "\n" not in first.strip() and BYLINE.match(first.strip("*_# \n")) and rest.strip():
        return rest
    return body


# Titles that come from file metadata are often the authoring app's, not the book's
APP_PREFIX = re.compile(r"^(?:Microsoft\s+(?:Word|PowerPoint|Excel)|Pages|Google\s+Docs)\s*[-–:]\s*", re.IGNORECASE)
FILE_EXTENSION = re.compile(r"\.(?:docx?|pdf|txt|md|rtf|odt|pages|epub)$", re.IGNORECASE)
BYLINE = re.compile(r"^\s*(?:written\s+)?by\s+([^\n]{2,80}?)\s*$", re.IGNORECASE)
SITE_SUFFIX = re.compile(r"\s+[-–|]\s+Wikipedia$", re.IGNORECASE)
# Words that show "author" metadata is really page furniture (Wikipedia's "Authority control
# databases...") or a placeholder (Calibre's "Unknown"), not a person
AUTHOR_JUNK = re.compile(
    r"\b(?:authority|control|databases?|wikipedia|wikimedia|contributors|retrieved|isbn|copyright"
    r"|rights reserved|unknown|anonymous|admin(?:istrator)?)\b",
    re.IGNORECASE,
)


def clean_title(title: str | None) -> str | None:
    """'Microsoft Word - All Tomorrows.doc' -> 'All Tomorrows'; 'my_book' -> 'my book'."""
    if not title:
        return None
    title = title.strip().strip("{}\\").strip()  # "}Avengers..." left over from an .rtf
    title = SITE_SUFFIX.sub("", FILE_EXTENSION.sub("", APP_PREFIX.sub("", title)))
    if " " not in title:
        title = title.replace("_", " ")
    return re.sub(r"\s+", " ", title).strip() or None


def clean_author(author: str | None) -> str | None:
    """Keep a plausible person's name; drop metadata junk. 'By Jane Doe' -> 'Jane Doe'."""
    author = re.sub(r"^\s*by\s+", "", author or "", flags=re.IGNORECASE).strip(" .,;\n\t")
    if not author or len(author) > 80 or len(author.split()) > 8:
        return None
    if re.search(r"\d|https?:|www\.|@", author) or AUTHOR_JUNK.search(author):
        return None
    return author


def find_byline(text: str) -> str | None:
    """An author named near the top: a line like "by C. M. Kosemen" in the first few lines."""
    lines = [line for line in text.split("\n")[:12] if line.strip()][:6]
    for line in lines:
        if match := BYLINE.match(line.strip("*_# ")):
            return match[1].strip(" .,")
    return None


def _words(blocks) -> int:
    return sum(len(b.text.split()) for b in blocks)


def split_long_sections(sections: list[Section], part_words: int = PART_WORDS) -> list[Section]:
    """Cut sections longer than part_words into parts, only between blocks (never mid-paragraph)."""
    result: list[Section] = []
    for section in sections:
        if _words(section.blocks) <= part_words * 1.5:  # a little over is fine: no 2-minute stub parts
            result.append(section)
            continue
        parts: list[list] = [[]]
        for block in section.blocks:
            if _words(parts[-1]) >= part_words:
                parts.append([])
            parts[-1].append(block)
        if len(parts) > 1 and _words(parts[-1]) < part_words / 3:  # a short tail joins the part before
            parts[-2].extend(parts.pop())
        for number, blocks in enumerate(parts, start=1):
            title = f"{section.title} · Part {number}" if section.title else f"Part {number}"
            result.append(Section(title=title, blocks=blocks))
    return result


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
    words = _words(blocks)
    speakers = list(dict.fromkeys(b.speaker for b in blocks if b.speaker))
    return Stats(
        characters=len(text),
        words=words,
        sentences=sum(len(b.sentences) for b in blocks),
        speakers=speakers,
        estimated_minutes=round(words / WORDS_PER_MINUTE, 1),
    )


def parse_text(text: str, title: str | None = None, author: str | None = None) -> ParsedDocument:
    text = normalize(text)
    text, header_title, header_author = strip_gutenberg(text)  # licence text is never read aloud
    text = drop_back_matter(drop_contents(text))
    detected_title, body = _leading_title(text)
    body = _drop_leading_byline(body)

    if looks_like_screenplay(body):
        doc_format, sections = "screenplay", parse_screenplay(body)
    else:
        markdown_title, sections = parse_prose(body)
        detected_title = detected_title or markdown_title
        doc_format = "prose"

    sections = split_long_sections(sections)
    _finalize(sections)
    return ParsedDocument(
        title=clean_title(detected_title or header_title or title),
        author=clean_author(author) or find_byline(text) or clean_author(header_author),
        format=doc_format,
        sections=sections,
        stats=_stats(text, sections),
    )

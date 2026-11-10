"""Remove text that should never be read aloud, before the structure is parsed.

- Project Gutenberg licence blocks (everything outside the START/END markers). The header's
  "Title:" and "Author:" lines are kept as metadata.
- Contents pages: a "Contents" line with the list after it, or a run of "Title ..... 12" lines.
"""

import re

GUTENBERG_START = re.compile(r"^\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*$", re.IGNORECASE | re.MULTILINE)
GUTENBERG_END = re.compile(r"^\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*$", re.IGNORECASE | re.MULTILINE)
HEADER_FIELD = re.compile(r"^(Title|Author):\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

CONTENTS_LINE = re.compile(r"^#*\s*(?:table of )?contents\.?$", re.IGNORECASE)
TOC_ENTRY = re.compile(r"^.{2,80}?(?:\s{2,}|\s*\.{3,}\s*)\d{1,4}$")  # "The Harbour      3", "Night .... 12"
MAX_ENTRY_LENGTH = 80


def strip_gutenberg(text: str) -> tuple[str, str | None, str | None]:
    """Return (the book between the markers, title, author). Text without markers is unchanged."""
    start = GUTENBERG_START.search(text)
    if not start:
        return text, None, None
    fields = {key.lower(): value for key, value in HEADER_FIELD.findall(text[: start.start()])}
    end = GUTENBERG_END.search(text, start.end())
    body = text[start.end() : end.start() if end else len(text)]
    return body.strip("\n"), fields.get("title"), fields.get("author")


def drop_contents(text: str) -> str:
    lines = text.split("\n")
    remove: set[int] = set()

    # A "Contents" line near the start, then the dense run of short lines that follows it
    for i, line in enumerate(lines[: max(40, len(lines) // 3)]):
        if not CONTENTS_LINE.match(line.strip()):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        k = j
        while k < len(lines) and lines[k].strip() and len(lines[k].strip()) <= MAX_ENTRY_LENGTH:
            k += 1
        if k - j >= 2:
            remove.update(range(i, k))

    # Three or more consecutive "title ... page number" lines, anywhere
    run: list[int] = []
    for i, line in enumerate([*lines, ""]):
        if line.strip() and TOC_ENTRY.match(line.strip()):
            run.append(i)
            continue
        if len(run) >= 3:
            remove.update(run)
        run = []

    return "\n".join(line for i, line in enumerate(lines) if i not in remove)

"""Remove text that should never be read aloud, before the structure is parsed.

- Project Gutenberg licence blocks (everything outside the START/END markers). The header's
  "Title:" and "Author:" lines are kept as metadata.
- Contents pages: a "Contents" line with the list after it, or a run of "Title ..... 12" lines.
- Back matter on web pages: References, Notes, Sources, External links, See also...
"""

import re

GUTENBERG_START = re.compile(r"^\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*$", re.IGNORECASE | re.MULTILINE)
GUTENBERG_END = re.compile(r"^\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*$", re.IGNORECASE | re.MULTILINE)
HEADER_FIELD = re.compile(r"^(Title|Author):\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

CONTENTS_LINE = re.compile(r"^#*\s*(?:table of )?contents\.?$", re.IGNORECASE)
TOC_ENTRY = re.compile(r"^.{2,80}?(?:\s{2,}|\s*\.{3,}\s*)\d{1,4}$")  # "The Harbour      3", "Night .... 12"
# The same with one space ("The Harbour 3", as PDF extraction leaves it): only trusted when the
# numbers go up, line after line, like page numbers in a contents list. At most 3 digits, so a
# short timeline ("Born in 1901", "Died in 1960") is never taken for a contents page.
LOOSE_TOC_ENTRY = re.compile(r"^(?P<title>\D.{1,78}?)\s+\.*\s*(?P<page>\d{1,3})$")
MAX_ENTRY_LENGTH = 80

BACK_MATTER = (r"(?:references|notes|footnotes|endnotes|sources|citations|bibliography|works cited"
               r"|further reading|external links|see also)")  # fmt: skip
MARKDOWN_BACK_MATTER = re.compile(rf"^(#{{1,6}})\s+{BACK_MATTER}\s*:?\s*#*$", re.IGNORECASE)
PLAIN_BACK_MATTER = re.compile(rf"^{BACK_MATTER}\s*:?$", re.IGNORECASE)
MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s")


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

    # ... or with single spaces, when the page numbers rise: 3, 5, 7, 9
    run, pages = [], []
    for i, line in enumerate([*lines, ""]):
        match = LOOSE_TOC_ENTRY.match(line.strip()) if len(line.strip()) <= MAX_ENTRY_LENGTH else None
        if match and (not pages or int(match["page"]) > pages[-1]):
            run.append(i)
            pages.append(int(match["page"]))
            continue
        if len(run) >= 3:
            remove.update(run)
        run, pages = ([i], [int(match["page"])]) if match else ([], [])

    return "\n".join(line for i, line in enumerate(lines) if i not in remove)


def drop_back_matter(text: str) -> str:
    """Reference lists are never part of the story.

    Markdown (what the URL importer produces): a "## References" section is dropped up to the
    next heading of the same or a higher level. Plain text (a pasted article): a "References"
    line standing alone in the second half of the text drops everything after it.
    """
    lines = text.split("\n")
    kept: list[str] = []
    skipping_level: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        heading = MARKDOWN_HEADING.match(stripped)
        if skipping_level is not None:
            ends_section = heading and len(heading[1]) <= skipping_level and not MARKDOWN_BACK_MATTER.match(stripped)
            if not ends_section:
                continue
            skipping_level = None
        if match := MARKDOWN_BACK_MATTER.match(stripped):
            skipping_level = len(match[1])
            continue
        alone = i == 0 or not lines[i - 1].strip()
        if PLAIN_BACK_MATTER.match(stripped) and alone and i >= len(lines) // 2:
            break
        kept.append(line)
    return "\n".join(kept)

"""Detect and parse screenplays: formal format and the "NAME: line" style common in fan scripts.

Formal format (line-based):
    INT. CITADEL - NIGHT          <- scene heading: starts a new section
    A vast hall.                  <- action: read by the narrator
                KANG              <- character cue: who speaks next
             (quietly)            <- parenthetical: direction, NOT spoken
        Every timeline ends.      <- dialogue
"""

import re

from app.structure.models import Block, Section
from app.structure.prose import CHAPTER, clean_inline

SLUGLINE = re.compile(r"^\.?(?:INT|EXT|EST|INT\.?\s*/\s*EXT|I\s*/\s*E)[.\s]")
TRANSITION = re.compile(
    r"^(?:[A-Z ]+ TO:|FADE IN:|FADE OUT\.?|FADE TO BLACK\.?|CUT TO BLACK\.?|THE END\.?)$"
)
CUE = re.compile(r"^([A-Z][A-Z0-9 .#'’\-]*?)\s*(?:\(([^)]+)\))?$")
COLON_LINE = re.compile(r"^([A-Za-z][\w.'’\- ]{0,30}?)\s*(?:\(([^)]+)\))?\s*:\s+(\S.*)$")
PARENTHETICAL = re.compile(r"^\((.+)\)$")
NOT_SPEAKERS = {"NOTE", "NOTES", "TITLE", "WARNING", "TIP", "SUMMARY", "SOURCE", "UPDATE", "EDIT", "PS"}
EXTENSIONS = {"V.O.": "voice-over", "VO": "voice-over", "O.S.": "off-screen", "O.C.": "off-screen"}


def _direction(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if raw.upper().replace("’", "'") in {"CONT'D", "CONTD", "CONT."}:
        return None  # "continued": a page-break artefact, not a direction
    return EXTENSIONS.get(raw.upper(), raw)


def parse_cue(line: str) -> tuple[str, str | None] | None:
    """'KANG (V.O.)' -> ('KANG', 'voice-over'). None if the line isn't a character cue."""
    if len(line) > 40 or line != line.upper() or not re.search(r"[A-Z]", line):
        return None
    if SLUGLINE.match(line) or TRANSITION.match(line) or CHAPTER.match(line):
        return None
    match = CUE.match(line)
    if not match:
        return None
    name = re.sub(r"\s+", " ", match[1]).strip(" .")
    return (name, _direction(match[2])) if name else None


def parse_colon_line(line: str, allow_title_case: bool = True) -> tuple[str, str | None, str] | None:
    """'Kang (smiling): Every timeline ends.' -> ('KANG', 'smiling', 'Every timeline ends.').

    Title-case names ("Kang:") are only trusted in colon-style scripts; in a formal
    screenplay "The Council: twelve thrones." is action, so only ALL-CAPS names count.
    """
    match = COLON_LINE.match(line)
    if not match:
        return None
    name = match[1].strip()
    words = name.split()
    is_name_like = name.isupper() or (allow_title_case and all(w[0].isupper() for w in words))
    if len(words) > 3 or not is_name_like or name.upper() in NOT_SPEAKERS or CHAPTER.match(name):
        return None
    return name.upper(), _direction(match[2]), match[3].strip()


def looks_like_screenplay(text: str) -> bool:
    lines = [line.strip() for line in text.split("\n")]
    nonempty = [line for line in lines if line]
    if not nonempty:
        return False

    sluglines = sum(1 for line in nonempty if SLUGLINE.match(line))
    cues = sum(
        1
        for i, line in enumerate(lines[:-1])
        if line and lines[i + 1].strip() and parse_cue(line)
    )
    colon_lines = sum(1 for line in nonempty if parse_colon_line(line))

    return (
        sluglines >= 2
        or (sluglines >= 1 and cues >= 2)
        or (cues >= 4 and cues / len(nonempty) > 0.05)
        or (colon_lines >= 4 and colon_lines / len(nonempty) >= 0.25)
    )


def parse_screenplay(text: str) -> list[Section]:
    lines = [line.strip() for line in text.split("\n")]
    sections = [Section()]
    action: list[str] = []
    open_dialogue = False  # a colon-style line can continue on the next line
    colon_style = sum(1 for line in lines if parse_colon_line(line)) >= 4

    def add(kind, text: str, speaker=None, direction=None) -> None:
        text = clean_inline(text)
        if text:
            sections[-1].blocks.append(
                Block(kind=kind, text=text, speaker=speaker, direction=direction)
            )

    def flush_action() -> None:
        if action:
            add("action", " ".join(action))
            action.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < len(lines) else ""

        if not line:
            flush_action()
            open_dialogue = False
            i += 1
            continue

        if SLUGLINE.match(line) or CHAPTER.match(line):
            flush_action()
            if sections[-1].blocks:
                sections.append(Section())
            sections[-1].title = line
            add("scene_heading", line.lstrip("."))
        elif TRANSITION.match(line):
            flush_action()
            add("transition", line)
        elif colon := parse_colon_line(line, allow_title_case=colon_style):
            flush_action()
            speaker, direction, spoken = colon
            add("dialogue", spoken, speaker, direction)
            open_dialogue = True
            i += 1
            continue
        elif next_line and (cue := parse_cue(line)):
            flush_action()
            speaker, direction = cue
            spoken: list[str] = []
            i += 1
            while i < len(lines) and lines[i]:
                if paren := PARENTHETICAL.match(lines[i]):
                    if spoken:  # a mid-speech direction ends the current dialogue block
                        add("dialogue", " ".join(spoken), speaker, direction)
                        spoken = []
                    direction = _direction(paren[1])
                else:
                    spoken.append(lines[i])
                i += 1
            add("dialogue", " ".join(spoken), speaker, direction)
            continue
        elif paren := PARENTHETICAL.match(line):
            flush_action()
            add("action", paren[1])  # a standalone "(Kang smiles)" is stage action
            open_dialogue = False
        elif open_dialogue and sections[-1].blocks:
            last = sections[-1].blocks[-1]
            last.text = clean_inline(f"{last.text} {line}")
        else:
            action.append(line)

        open_dialogue = open_dialogue and not SLUGLINE.match(line)
        i += 1

    flush_action()
    return [s for s in sections if s.blocks]

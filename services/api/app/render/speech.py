"""What is actually *said* for a line, which can differ from what the reader shows."""

import re

SLUGLINE = re.compile(r"^\.?(INT\.?\s*/\s*EXT|I\s*/\s*E|INT|EXT|EST)\.?\s+(.+)$", re.IGNORECASE)
PREFIXES = {"INT": "Interior", "EXT": "Exterior", "EST": "Establishing"}


def _sentence_case(text: str) -> str:
    text = text.strip().lower()
    return text[:1].upper() + text[1:]


def speech_text(kind: str, text: str) -> str | None:
    """The words to synthesise, or None for a silent beat."""
    if not text.strip() or kind == "transition":
        return None  # "CUT TO:" is a pause, not speech (narration guide)

    if kind == "scene_heading" and (match := SLUGLINE.match(text)):
        # "INT. CITADEL THRONE ROOM - NIGHT" -> "Interior. Citadel throne room. Night."
        prefix = match[1].upper().replace(" ", "")
        spoken = PREFIXES.get(prefix, "Interior, exterior")
        parts = [_sentence_case(p) for p in re.split(r"\s+[-–—]\s+", match[2]) if p.strip()]
        return ". ".join([spoken, *parts]) + "."

    return text

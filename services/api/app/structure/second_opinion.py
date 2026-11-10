"""An optional AI second opinion on the lines the rules weren't sure about.

The rules (steps 2-5 of the revive) decide almost everything. What they can't decide is a short
line standing on its own that isn't a sentence and doesn't look like a heading: "A letter from
the hill" (a sentence-case chapter title?), "Show more" (a website button?), "Morning" (a
sub-heading, or a one-word paragraph?). Only those lines, with a peek at the text after each,
go to the model, which labels them by number. The answer is a few tokens per line.

Guardrails: off unless STRUCTURE_AI is set; only short doubtful lines can change (a long line
can never be deleted); screenplays are left alone; every change is written to document.notes;
if the model fails, the rules' result is kept as it was.
"""

import logging
import re

from app.config import settings
from app.structure import parse_text
from app.structure.models import ParsedDocument

log = logging.getLogger(__name__)

MAX_CHARS = 60
MAX_WORDS = 8
SENTENCE_END = (".", "!", "?", ",", ";", '"', "'", "”", "’", ")", "…")
LABELS = {"H", "S", "X", "K"}

PROMPT = """You check the structure of a text that will be read aloud as an audiobook.
Each numbered item below is a short line that stands on its own in the text; automatic rules
could not tell what it is. It is shown as: ...end of the text before it || THE LINE || start of
the text after it... Use both sides: a line after "here are the main points:" is a list item.
Label every item with exactly one letter:
H = a chapter or part title
S = a sub-heading inside a chapter
X = not part of the work: website or app interface text ("Show more", "Translate post",
    "Replying to @...", view counts, timestamps), ads, page furniture
K = ordinary text of the work, keep it (a one-word answer, a name, a line of verse)
Answer with one line per item, "<number> <letter>", and nothing else."""


def doubtful_blocks(document: ParsedDocument) -> list[tuple[int, int]]:
    """(section, block) positions of short standalone paragraphs that don't read as sentences."""
    found = []
    for s, section in enumerate(document.sections):
        for b, block in enumerate(section.blocks):
            text = block.text.strip()
            short = len(text) <= MAX_CHARS and len(text.split()) <= MAX_WORDS
            if block.kind == "paragraph" and text and short and not text.endswith(SENTENCE_END):
                found.append((s, b))
    return found


def _context(document: ParsedDocument, s: int, b: int) -> tuple[str, str]:
    """The end of the text before the line and the start of the text after it (60 characters each)."""
    blocks = [block for section in document.sections for block in section.blocks]
    flat = sum(len(section.blocks) for section in document.sections[:s]) + b
    before = next((block.text for block in reversed(blocks[:flat]) if block.text), "")
    after = next((block.text for block in blocks[flat + 1 :] if block.text), "")
    return before[-60:], after[:60]


def _ask_claude(payload: str) -> str:
    import anthropic  # imported only when this provider is chosen

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.structure_ai_claude_model,
        max_tokens=4000,
        system=PROMPT,
        messages=[{"role": "user", "content": payload}],
        output_config={"effort": "low"},  # a short labelling task: little thinking needed
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined")
    log.info("Second opinion %s: %s tokens in, %s out", settings.structure_ai_claude_model,
             response.usage.input_tokens, response.usage.output_tokens)
    return "".join(block.text for block in response.content if block.type == "text")


def _ask_gemini(payload: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.structure_ai_gemini_model,
        contents=payload,
        config=types.GenerateContentConfig(system_instruction=PROMPT, temperature=0, max_output_tokens=4000),
    )
    usage = response.usage_metadata
    log.info("Second opinion %s: %s tokens in, %s out", settings.structure_ai_gemini_model,
             usage.prompt_token_count if usage else "?", usage.candidates_token_count if usage else "?")
    return response.text or ""


def _parse_labels(answer: str, count: int) -> dict[int, str]:
    labels = {}
    for line in answer.splitlines():
        if (match := re.match(r"^\s*(\d+)\s*[|:.\-)]?\s*([A-Za-z])\b", line)) and match[2].upper() in LABELS:
            number = int(match[1])
            if 1 <= number <= count:
                labels[number] = match[2].upper()
    return labels


def _as_markdown(document: ParsedDocument, changes: dict[tuple[int, int], str]) -> str:
    """Write the parsed document back out as markdown, with the model's labels applied."""
    lines = []
    for s, section in enumerate(document.sections):
        for b, block in enumerate(section.blocks):
            label = changes.get((s, b))
            if label == "X":
                continue
            if label == "H" or (block.kind == "heading" and b == 0):
                lines.append(f"## {block.text}")
            elif label == "S" or block.kind == "heading":
                lines.append(f"### {block.text}")
            elif block.kind == "quote":
                lines.append(f"> {block.text}")
            elif block.kind == "list_item":
                lines.append(f"- {block.text}")
            elif block.kind == "scene_break":
                lines.append("* * *")
            else:
                lines.append(block.text)
    return "\n\n".join(lines)


def second_opinion(document: ParsedDocument, provider: str | None = None) -> ParsedDocument:
    provider = provider or settings.structure_ai
    if provider == "off" or document.format != "prose":
        return document
    doubtful = doubtful_blocks(document)
    if not doubtful:
        return document

    lines = []
    for n, (s, b) in enumerate(doubtful, start=1):
        before, after = _context(document, s, b)
        lines.append(f"{n}. ...{before} || {document.sections[s].blocks[b].text} || {after}...")
    payload = "\n".join(lines)
    try:
        answer = _ask_claude(payload) if provider == "claude" else _ask_gemini(payload)
    except Exception as error:  # noqa: BLE001 - an optional helper must never break an import
        log.warning("AI second opinion (%s) failed: %r", provider, error)
        document.notes.append(f"AI second opinion ({provider}) was unavailable; the rules' structure is kept.")
        return document

    labels = _parse_labels(answer, len(doubtful))
    changes = {doubtful[n - 1]: label for n, label in labels.items() if label != "K"}
    if not changes:
        document.notes.append(f"AI second opinion ({provider}) checked {len(doubtful)} lines and changed nothing.")
        return document

    revised = parse_text(_as_markdown(document, changes), title=document.title, author=document.author)
    described = {"H": "chapter title", "S": "sub-heading", "X": "skipped"}
    listed = "; ".join(
        f'"{document.sections[s].blocks[b].text}" → {described[label]}' for (s, b), label in changes.items()
    )
    revised.notes = [*document.notes, f"AI second opinion ({provider}) changed {len(changes)} lines: {listed}"]
    return revised

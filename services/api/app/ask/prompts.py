"""The reading companion's prompt: the question, grounded in where the reader is."""

from app.models import Document, Segment

# The model reads the book from the start up to where the reader is, so "so far"
# questions get real answers and nothing later can leak. A couple of lines past the
# position finish the thought being spoken. Capped, keeping the most recent text, so
# one question stays well inside the free tier's tokens per minute (~200k chars ≈ 50k tokens).
LOOKAHEAD_LINES = 2
MAX_CONTEXT_CHARS = 200_000

SYSTEM = """You are a knowledgeable, friendly reading companion inside an audiobook app. The reader paused to ask about what they're reading.

- You are given the text from the beginning up to where the reader is. Treat it as everything they know.
- Never reveal or hint at anything that happens after that point, even if you know the work. If asked, say you'll keep it spoiler-free.
- Answer directly and concisely: usually two to five sentences, in plain language.
- Ground your answer in the text. Say clearly when you go beyond it (general knowledge) or when the text doesn't say.
- For the meaning of a word or phrase, give its meaning in this context first.
- Formatting: plain paragraphs. **Bold** for names or key terms, and a short bulleted list ("- item"), are fine when they genuinely help. No headings, tables or code blocks."""


def _text_so_far(spoken: list[Segment], index: int | None, names: dict[str, str]) -> str:
    if index is None:
        return "(The reader's position is unknown, so no text is shared. Answer from the summary.)"

    def line(segment: Segment) -> str:
        if segment.block_kind == "dialogue":
            return f"{names.get(segment.role, segment.role.title())}: {segment.text}"
        return segment.text

    here = [f">>> {line(spoken[index])} <<< (the reader is here)"]
    here += [line(s) for s in spoken[index + 1 : index + LOOKAHEAD_LINES + 1]]
    before = "\n".join(line(s) for s in spoken[:index])
    # A very long book: the reader's line always stays; trim the oldest text, from a line start
    budget = max(0, MAX_CONTEXT_CHARS - sum(len(h) + 1 for h in here))
    if len(before) > budget:
        before = "(Earlier text omitted.)\n" + before[len(before) - budget :].split("\n", 1)[-1]
    return "\n".join(filter(None, [before, *here]))


def build_prompt(
    document: Document,
    question: str,
    selection: str | None,
    segment_id: int | None,
    history: list[tuple[str, str]],
) -> str:
    names = {p.cast_id: p.display_name for p in document.personas}
    spoken = [s for s in document.segments if s.text]
    index = next((i for i, s in enumerate(spoken) if s.id == segment_id), None)

    parts = [
        f"Work: {document.title or 'Untitled'} ({document.genre or document.format})",
        f"About the work: {document.summary or 'Not analysed yet.'}",
        f"Characters: {', '.join(n for c, n in names.items() if c != 'NARRATOR') or 'none'}",
        f"The text so far:\n{_text_so_far(spoken, index, names)}",
    ]
    if selection:
        parts.append(f'The reader selected this passage: "{selection.strip()}"')
    if history:
        conversation = "\n".join(f"{'Reader' if role == 'user' else 'You'}: {text}" for role, text in history)
        parts.append(f"Conversation so far:\n{conversation}")
    parts.append(f"The reader asks: {question.strip()}")
    return "\n\n".join(parts)

"""The reading companion's prompt: the question, grounded in where the reader is."""

from app.models import Document

CONTEXT_LINES = 12  # lines before and after the reader's position

SYSTEM = """You are a knowledgeable, friendly reading companion inside an audiobook app. The reader paused to ask about what they're reading.

- Answer directly and concisely: usually two to five sentences, in plain language.
- Ground your answer in the passage and the work. Say clearly when you go beyond the text (general knowledge) or when the text doesn't say.
- For the meaning of a word or phrase, give its meaning in this context first.
- Never invent events in the work, and don't reveal later parts of it unless asked.
- No headings. Short paragraphs, or a short list if it genuinely helps."""


def build_prompt(
    document: Document,
    question: str,
    selection: str | None,
    segment_id: int | None,
    history: list[tuple[str, str]],
) -> str:
    names = {p.cast_id: p.display_name for p in document.personas}
    spoken = [s for s in document.segments if s.text]

    surrounding = "(The reader's position is unknown.)"
    index = next((i for i, s in enumerate(spoken) if s.id == segment_id), None)
    if index is not None:
        window = spoken[max(0, index - CONTEXT_LINES) : index + CONTEXT_LINES + 1]
        surrounding = "\n".join(
            f"{names.get(s.role, s.role.title())}: {s.text}" if s.block_kind == "dialogue" else s.text for s in window
        )

    parts = [
        f"Work: {document.title or 'Untitled'} ({document.genre or document.format})",
        f"About the work: {document.summary or 'Not analysed yet.'}",
        f"Characters: {', '.join(n for c, n in names.items() if c != 'NARRATOR') or 'none'}",
        f"Text around where the reader is:\n{surrounding}",
    ]
    if selection:
        parts.append(f'The reader selected this passage: "{selection.strip()}"')
    if history:
        conversation = "\n".join(f"{'Reader' if role == 'user' else 'You'}: {text}" for role, text in history)
        parts.append(f"Conversation so far:\n{conversation}")
    parts.append(f"The reader asks: {question.strip()}")
    return "\n\n".join(parts)

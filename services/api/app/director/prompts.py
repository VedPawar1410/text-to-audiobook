from app.director.schema import DocumentDirection
from app.director.vocabulary import EMOTIONS, GENRES

# ~150k tokens: comfortably inside Gemini Flash's 1M-token window, with room to spare
MAX_DOCUMENT_CHARS = 600_000

SYSTEM = """You are the director of an audiobook. You decide how every line is performed.

Rules:
- Restraint: about 70% of lines are neutral or warm at intensity 1. Use intensity 3 only for true peaks. Over-acting is the most common failure.
- Use only the emotion names you are given.
- Speakers: a character speaks only their own dialogue. Everything else (narration, action, headings, and dialogue tags such as "he said") is NARRATOR.
- Directions in the text, like (quietly) or (angry), tell you HOW a line is said. They are never spoken.
- Pauses are milliseconds of silence, 0 to 3000. Use longer pauses before reveals and after dramatic lines; most lines need little.
- Emphasis: at most 2 words per line, copied exactly from the line, and only when stress changes the meaning or the drama.
- Describe voices by texture, pace and attitude. Never name a real actor or person."""


def render_lines(lines) -> str:
    """One line per sentence: '[12] (dialogue | KANG | quietly) Every timeline ends.'"""
    rendered = []
    for line in lines:
        tags = [line.kind, line.speaker, line.direction]
        rendered.append(f"[{line.index}] ({' | '.join(t for t in tags if t)}) {line.text}")
    return "\n".join(rendered)


def document_prompt(*, title: str | None, format: str, speakers: list[str], lines) -> str:
    genres = "\n".join(f"- {name}: {profile}" for name, profile in GENRES.items())
    if speakers:
        cast_rule = (
            "These speaker ids come from the script. Include every one in the cast, "
            f"using exactly this id: {', '.join(speakers)}."
        )
    else:
        cast_rule = (
            "Identify the characters who speak (quoted dialogue). Give each a short "
            "UPPERCASE id, e.g. MARY. If nobody speaks, the cast is empty."
        )

    text = render_lines(lines)
    if len(text) > MAX_DOCUMENT_CHARS:
        text = text[:MAX_DOCUMENT_CHARS] + "\n[... the rest is omitted ...]"

    return f"""Read this whole {format} and plan its audiobook performance.

Title: {title or "Untitled"}

Choose the genre from:
{genres}

{cast_rule}
Choose a narrator gender and accent that suit the material, and describe the narrator's style in one sentence.
Summarise the work in two or three sentences.

TEXT:
{text}"""


def lines_prompt(direction: DocumentDirection, context, lines) -> str:
    emotions = "\n".join(f"- {name}: {emotion.delivery}" for name, emotion in EMOTIONS.items())
    cast = "\n".join(f"- {m.id}: {m.voice_description}" for m in direction.cast) or "- (no characters)"
    context_block = (
        f"Context, already performed (do not label):\n{render_lines(context)}\n\n" if context else ""
    )
    return f"""Genre: {direction.genre}, {GENRES[direction.genre]}
Narrator (NARRATOR): {direction.narrator_style}
Cast:
{cast}

Emotions you may use:
{emotions}

{context_block}Label every one of these lines, using its [index]:
{render_lines(lines)}"""

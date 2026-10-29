"""Machine-readable narration vocabulary. Human version: docs/narration-guide.md.

One source for both consumers: the director's prompt (which emotions and genres
exist) and, in PR 7, the renderer (how each emotion becomes Kokoro speed + pauses).
"""

from dataclasses import dataclass
from typing import Literal

EmotionName = Literal[
    "neutral", "warm", "joyful", "playful", "tender", "melancholic", "grief", "anxious",
    "suspenseful", "ominous", "angry", "cold", "determined", "awe", "surprised",
    "sarcastic", "urgent", "weary", "whispering", "authoritative",
]  # fmt: skip

GenreName = Literal[
    "screenplay", "scifi_action", "fantasy", "thriller", "horror", "romance", "comedy",
    "childrens", "history", "biography", "journalism", "art", "technical", "poetry",
    "self_help", "news", "general",
]  # fmt: skip


@dataclass(frozen=True)
class Emotion:
    delivery: str  # how a human narrator performs it (goes into the prompt)
    speed: float  # Kokoro speed at intensity 2
    pause_before_ms: int
    pause_after_ms: int


EMOTIONS: dict[str, Emotion] = {
    "neutral": Emotion("clear and engaged, not flat", 1.00, 0, 250),
    "warm": Emotion("softer onset, a slight smile in the voice", 0.97, 0, 300),
    "joyful": Emotion("brighter, lifted, quicker", 1.06, 0, 250),
    "playful": Emotion("bouncy rhythm, light teasing stress", 1.05, 0, 250),
    "tender": Emotion("quiet and close, elongated vowels", 0.92, 150, 450),
    "melancholic": Emotion("lower energy, falling ends", 0.92, 200, 500),
    "grief": Emotion("heavy and halting, breaks between phrases", 0.86, 400, 800),
    "anxious": Emotion("quick, clipped, rising", 1.08, 0, 150),
    "suspenseful": Emotion("slow and quiet, holding back", 0.88, 500, 700),
    "ominous": Emotion("low and deliberate, every word placed; also menacing", 0.85, 400, 700),
    "angry": Emotion("hard consonants, forceful, faster bursts", 1.07, 0, 300),
    "cold": Emotion("flat, slow, precise and clipped; also contemptuous", 0.93, 200, 400),
    "determined": Emotion("firm, forward-moving, strong ends; also heroic", 1.02, 100, 350),
    "awe": Emotion("breathy, slow, opening up", 0.90, 300, 600),
    "surprised": Emotion("sudden lift, a quick intake", 1.04, 150, 300),
    "sarcastic": Emotion("exaggerated stress, drawn-out key word", 0.97, 100, 350),
    "urgent": Emotion("fast with no gaps, pressing forward", 1.12, 0, 100),
    "weary": Emotion("slow and heavy, sighing", 0.90, 200, 500),
    "whispering": Emotion("hushed and intimate; also secretive", 0.92, 200, 400),
    "authoritative": Emotion("measured, declarative, level", 0.98, 100, 400),
}

GENRES: dict[str, str] = {
    "screenplay": "crisp neutral narrator for action lines; scene headings as short cues; characters carry the drama",
    "scifi_action": "neutral with tension; shorter pauses in fights, suspense before reveals",
    "fantasy": "warm, slightly grand; awe for world reveals",
    "thriller": "controlled; long pauses before reveals, clipped anxiety in chases",
    "horror": "quiet and slow, long silences, ominous for the threat",
    "romance": "warm; tender in intimate moments",
    "comedy": "playful; a short pause before the punchline and a beat after",
    "childrens": "warm and animated; bigger character contrast, slow and clear",
    "history": "authoritative and measured; dates, names and numbers said clearly",
    "biography": "warm and personal; reflective passages slow down",
    "journalism": "neutral and brisk, conversational",
    "art": "warm and contemplative; descriptive passages unhurried",
    "technical": "authoritative and clear; slow down on new terms",
    "poetry": "tender and slow; pause at line breaks, never rushed",
    "self_help": "warm and motivating; direct and conversational",
    "news": "neutral and authoritative; even and unemotional",
    "general": "neutral and engaged",
}

"""The parsed shape of a document: sections → blocks → sentences.

Everything that gets spoken is a Block (including chapter and scene headings),
so later stages (director, renderer, reader) only ever walk blocks in order.
"""

from typing import Literal

from pydantic import BaseModel, Field

BlockKind = Literal[
    # prose
    "heading", "paragraph", "list_item", "quote", "scene_break",
    # screenplay
    "scene_heading", "action", "dialogue", "transition",
]  # fmt: skip


class Block(BaseModel):
    kind: BlockKind
    text: str
    speaker: str | None = None  # dialogue only, e.g. "KANG"
    direction: str | None = None  # e.g. "quietly" from "(quietly)", or "voice-over"
    sentences: list[str] = Field(default_factory=list)  # the units the TTS renders


class Section(BaseModel):
    title: str | None = None  # navigation label: chapter or scene heading
    blocks: list[Block] = Field(default_factory=list)


class Stats(BaseModel):
    characters: int
    words: int
    sentences: int
    speakers: list[str]  # dialogue speakers, in order of first appearance
    estimated_minutes: float  # at a typical audiobook pace of 150 words per minute


class ParsedDocument(BaseModel):
    title: str | None
    format: Literal["prose", "screenplay"]
    sections: list[Section]
    stats: Stats

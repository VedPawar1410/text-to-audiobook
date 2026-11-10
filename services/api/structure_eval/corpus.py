"""One synthetic book, written for these tests (no real book text is ever committed).

Paragraphs are built from a pool of original sentences with a fixed random seed, so the
book is the same on every run. Plain ASCII and no digits on purpose: the PDF renderer only
handles Latin-1, and any bare number in the spoken output can then only be a leaked page number.
"""

import random
from dataclasses import dataclass, field

SENTENCES = [
    "The rain had not stopped since morning.",
    "Mara pulled her coat tighter and watched the harbour lights blink awake one by one.",
    "Nobody in the village remembered who had built the lighthouse.",
    "Its keeper wrote every passing ship into a ledger with a green cover.",
    "The ledger was older than the keeper, and some of its pages were stuck together with salt.",
    "A gull landed on the railing and studied her with one yellow eye.",
    "She had come for an answer, and she was not going to leave without one.",
    "Down on the quay, the fishermen argued about the weather in low voices.",
    "The wind changed direction twice before noon.",
    "Somewhere below, a door banged open and shut, open and shut.",
    "Tobias kept his hands in his pockets, as if the cold could not find them there.",
    "He had promised to wait, but waiting was never something he did well.",
    "The stairs wound upward in a tight spiral, worn smooth in the middle of every step.",
    "At the top, the great lamp turned slowly, throwing its beam across the water.",
    "Mara counted the seconds between flashes without meaning to.",
    "The last entry in the ledger was written in a hand she did not recognise.",
    "It named a ship that had never arrived.",
    "Outside, the tide was turning, pulling the boats gently against their ropes.",
    "Tobias said nothing for a long time.",
    "When he finally spoke, his voice was barely louder than the sea.",
    "The village had kept this secret for longer than anyone could say.",
    "Every family had a version of the story, and none of them agreed.",
    "The baker's version had a storm in it; the schoolteacher's had a fire.",
    "Mara believed neither, but she wrote both down anyway.",
    "Night came early, the way it always did at the end of autumn.",
    "They lit a lantern and spread the old charts across the table.",
    "Pencil marks crossed the paper in a pattern that looked almost deliberate.",
    "One line led straight out past the rocks and simply stopped.",
    "The kettle began to whistle, and both of them jumped.",
    "Morning brought a thin grey light and a boat that nobody had seen leave.",
    "It was tied to the end of the quay, its deck wet and empty.",
    "Mara walked the length of it twice before she let herself climb aboard.",
    "In the cabin, a coat hung on a hook as if its owner had just stepped out.",
    "The pockets held a compass, a pencil stub and a folded page from the ledger.",
    "She smoothed the page flat on her knee and read it slowly.",
    "Tobias watched from the quay, his face unreadable.",
    "The sea was calm now, almost polite, as though nothing had ever happened.",
    "By evening the whole village knew, and by morning they had all decided what it meant.",
    "Mara closed the ledger and set it back on its shelf.",
    "Some questions, she thought, were better answered slowly.",
]

DIALOGUE = [
    '"Yes."',
    '"Where were you?" she asked.',
    '"Not tonight," said Tobias.',
    '"You should have told me."',
    '"Look at the tide."',
    '"Then we wait."',
]

TITLE = "The Keeper's Ledger"
AUTHOR = "Mara Ellison"


@dataclass
class Chapter:
    name: str  # e.g. "The Harbour"; each format renders its own heading around it
    items: list[tuple[str, str]] = field(default_factory=list)  # ("p", text) or ("sub", subheading)


def _paragraph(rng: random.Random) -> str:
    return " ".join(rng.sample(SENTENCES, rng.randint(2, 6)))


def build_book(paragraphs_per_chapter: int = 11, seed: int = 7) -> list[Chapter]:
    rng = random.Random(seed)
    names = ["The Harbour", "A Letter from the Hill", "Night Crossing", "What the Tide Left"]
    subheadings = {0: "The First Night", 2: "Morning"}
    chapters = []
    for number, name in enumerate(names):
        chapter = Chapter(name)
        for index in range(paragraphs_per_chapter):
            if number in subheadings and index == paragraphs_per_chapter // 2:
                chapter.items.append(("sub", subheadings[number]))
            if index in (3, 8):  # short one-line dialogue paragraphs: easy to mistake for headings
                chapter.items.append(("p", rng.choice(DIALOGUE)))
            chapter.items.append(("p", _paragraph(rng)))
        chapters.append(chapter)
    return chapters

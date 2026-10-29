"""Auto-cast Kokoro voices from the director's hints. Deterministic: no LLM here.

The best-rated voice that fits goes to the narrator, then to each character in
order of appearance. Gender is respected strictly; accent is a preference that
relaxes when the pool runs out. Users can re-cast anything in the UI (PR 6).
"""

from collections import Counter
from dataclasses import dataclass

from app.director.director import NARRATOR
from app.director.schema import DocumentDirection
from app.tts.kokoro_voices import QUALITY_ORDER, VOICES_BY_ID

AGE_SPEED = {"child": 1.06, "young": 1.02, "adult": 1.0, "elder": 0.93}
NOVELTY_VOICES = {"am_santa"}  # fun, but never chosen automatically


@dataclass(frozen=True)
class PersonaPlan:
    cast_id: str
    display_name: str
    gender: str
    age: str
    accent: str
    description: str
    voice: str
    speed: float


def candidate_voices(gender: str, accent: str) -> list[str]:
    """Voices for a role, best first: exact accent matches, then any accent."""
    ranked = [v for v in QUALITY_ORDER if v not in NOVELTY_VOICES]

    def gender_ok(voice_id: str) -> bool:
        return gender == "unknown" or VOICES_BY_ID[voice_id].gender == gender

    def accent_ok(voice_id: str) -> bool:
        return accent == "any" or VOICES_BY_ID[voice_id].accent.lower() == accent

    exact = [v for v in ranked if gender_ok(v) and accent_ok(v)]
    relaxed = [v for v in ranked if gender_ok(v) and v not in exact]
    return exact + relaxed


def auto_cast(direction: DocumentDirection) -> list[PersonaPlan]:
    narrator_voice = candidate_voices(direction.narrator_gender, direction.narrator_accent)[0]
    plans = [
        PersonaPlan(
            cast_id=NARRATOR,
            display_name="Narrator",
            gender=direction.narrator_gender,
            age="adult",
            accent=direction.narrator_accent,
            description=direction.narrator_style,
            voice=narrator_voice,
            speed=1.0,
        )
    ]
    uses = Counter({narrator_voice: 1})

    for member in direction.cast:
        options = candidate_voices(member.gender, member.accent)
        unused = [v for v in options if uses[v] == 0]
        # When every fitting voice is taken, reuse the least-used one
        voice = unused[0] if unused else min(options, key=lambda v: uses[v])
        uses[voice] += 1
        plans.append(
            PersonaPlan(
                cast_id=member.id,
                display_name=member.display_name,
                gender=member.gender,
                age=member.age,
                accent=member.accent,
                description=member.voice_description,
                voice=voice,
                speed=AGE_SPEED[member.age],
            )
        )
    return plans

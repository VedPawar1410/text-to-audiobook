# Narration guide

This guide is how the AI **director** decides how text should be performed. It's the source for:

1. the director's prompt (PR 5): the emotion vocabulary, genre profiles and structural rules below;
2. the **render mapping** (PR 7): how each direction becomes actual speed and pauses in Kokoro, the free engine. Kokoro can't change emotion directly.

It reflects common practice in professional audiobook narration: a neutral-but-engaged narrator, distinct but restrained character voices, pacing as the main expressive tool, and silence used deliberately.

---

## 1. Delivery dimensions

Every segment (roughly one sentence) gets these fields:

| Field | Values | What it controls |
|---|---|---|
| `speaker` | `narrator` or a character id | Which voice (persona) reads it |
| `emotion` | one of the 20 below | The intended feeling |
| `intensity` | 1 (subtle) · 2 (clear) · 3 (strong) | How far to push it; most lines are 1 |
| `pace` | `slow` · `normal` · `fast` | Speaking rate |
| `pause_before_ms` / `pause_after_ms` | 0–3000 | Silence; the strongest tool for suspense and weight |
| `emphasis` | list of words | Words to lean on (used by engines that support stress) |
| `nonverbal` | `sigh`, `laugh`, `breath`, `gasp`… | Only for engines that support them (OpenAI, ElevenLabs); ignored by Kokoro |

**Restraint rule:** about 70% of narration in most books is `neutral` or `warm` at intensity 1. Over-acting is the most common failure of AI narration. The director should save intensity 3 for real peaks.

## 2. Emotion vocabulary (20)

Each emotion lists how a human narrator would deliver it, and the render mapping used for Kokoro (speed multiplier and pauses).

| Emotion | Human delivery | Kokoro speed | Pause before / after (ms) |
|---|---|---|---|
| `neutral` | Clear and engaged, not flat | 1.00 | 0 / 250 |
| `warm` | Softer onset, a slight smile in the voice | 0.97 | 0 / 300 |
| `joyful` | Brighter, lifted, quicker | 1.06 | 0 / 250 |
| `playful` | Bouncy rhythm, light teasing stress | 1.05 | 0 / 250 |
| `tender` | Quiet and close, elongated vowels | 0.92 | 150 / 450 |
| `melancholic` | Lower energy, falling ends | 0.92 | 200 / 500 |
| `grief` | Heavy and halting, breaks between phrases | 0.86 | 400 / 800 |
| `anxious` | Quick, clipped, rising | 1.08 | 0 / 150 |
| `suspenseful` | Slow and quiet, holding back | 0.88 | 500 / 700 |
| `ominous` / `menacing` | Low and deliberate, every word placed | 0.85 | 400 / 700 |
| `angry` | Hard consonants, forceful, faster bursts | 1.07 | 0 / 300 |
| `cold` / `contemptuous` | Flat, slow, precise and clipped | 0.93 | 200 / 400 |
| `determined` / `heroic` | Firm, forward-moving, strong ends | 1.02 | 100 / 350 |
| `awe` | Breathy, slow, opening up | 0.90 | 300 / 600 |
| `surprised` | Sudden lift, a quick intake | 1.04 | 150 / 300 |
| `sarcastic` | Exaggerated stress, drawn-out key word | 0.97 | 100 / 350 |
| `urgent` | Fast with no gaps, pressing forward | 1.12 | 0 / 100 |
| `weary` | Slow and heavy, sighing | 0.90 | 200 / 500 |
| `whispering` / `secretive` | Hushed, intimate | 0.92 | 200 / 400 |
| `authoritative` | Measured, declarative, level | 0.98 | 100 / 400 |

**Intensity scales the deviation from neutral:** `speed = 1 + (table_speed − 1) × intensity_factor`, where the factor is 0.5 for intensity 1, 1.0 for 2 and 1.4 for 3. Pauses scale the same way. The **pace** field multiplies on top: slow ×0.92, fast ×1.08. The final speed is clamped to the range 0.75–1.25, because beyond that Kokoro sounds unnatural.

## 3. Narrator vs character voices

- **The narrator** is the anchor. Keep it consistent across the whole book and give it less emotional range than the characters. It *colors* moments; it doesn't *act* them.
- **Characters** each get a distinct persona: a different base voice, and a slightly different default speed if needed. Differentiate them through voice choice first and emotion second.
- **Dialogue tags** ("he said quietly") go to the narrator, and the adverb informs the *character's* line delivery ("quietly" → `whispering`, intensity 1).
- **Internal thoughts** (often in italics) are read by the narrator, more softly (`tender` or `neutral`, slightly slower).

## 4. Genre profiles

The director first classifies the document, then applies a profile as the *default* for every segment. Individual lines can still deviate.

| Genre | Narrator default | Pace | Signature moves |
|---|---|---|---|
| **Screenplay** | `neutral`, crisp, present tense | normal | Sluglines (`INT. CITADEL – NIGHT`) read as a short scene cue followed by a 900ms pause. Action lines go to the narrator. Character cues are **not spoken**; they assign the speaker. **Parentheticals are direction, not text**: `(whispering)` sets emotion and isn't read. Transitions (`CUT TO:`) are skipped or become a 1.2s pause. |
| **Sci-fi / action** | `neutral` with tension | normal → fast in action | Shorter pauses in fights; `suspenseful` builds before reveals; technical terms read cleanly |
| **Fantasy / epic** | `warm`, slightly grand | normal–slow | `awe` for world reveals; invented names said slowly and consistently |
| **Thriller / mystery** | `neutral`, controlled | normal | Long pauses before reveals; clipped `anxious` in chases |
| **Horror** | `suspenseful` low | slow | Quiet, long silences, `ominous` for the threat; never rushed |
| **Romance** | `warm` | normal–slow | `tender` in intimate moments; softer character voices |
| **Comedy** | `playful` | normal | **Timing**: a pause *before* the punchline (300–500ms) and a beat after |
| **Children's** | `warm`, animated | slow | Bigger character contrast (the one genre where intensity 2–3 is normal) and clear articulation |
| **History** | `authoritative` | normal–slow | Dates, names and numbers said clearly; quotations get a slight voice shift |
| **Biography / memoir** | `warm`, personal | normal | First person feels conversational; reflective passages slow down |
| **Journalism / magazine** | `neutral`, brisk | normal–fast | Conversational; pull quotes are read as the quoted person (narrator with a slight shift) |
| **Art / criticism** | `warm`, contemplative | slow | Descriptive passages unhurried, letting images form; titles of works emphasized |
| **Science / technical / academic** | `authoritative`, clear | slow on new terms | Define, then pause. Equations and code are summarized, not read symbol by symbol. Tables are described ("a table comparing…"). |
| **Poetry** | `tender` / per poem | slow | Pause at line breaks (400ms) and stanza breaks (1s); respect the meter; no speeding up |
| **Self-help / business** | `warm`, motivating | normal | Direct address ("you") delivered conversationally; lists are clearly enumerated |
| **News** | `neutral`, authoritative | normal | Even, unemotional, with clear transitions between stories |

## 5. Structural reading rules

| Element | Treatment |
|---|---|
| Book / document title | Read once at the start, then a 1.5s pause |
| Chapter heading | "Chapter Seven. *The Last Timeline.*", then a 1.2s pause; a 2s silence *before* it, ending the previous chapter |
| Section subheading | Read, then a 700ms pause |
| Paragraph break | 450ms (narrative) or 350ms (non-fiction) |
| Scene break (`***`, `---`, blank lines) | 1.5s silence; not spoken |
| Bulleted / numbered list | Each item read as its own sentence with a 300ms gap; numbers spoken ("First… Second…") when numbered |
| Block quote | Same narrator, slightly slower (×0.96), with a 300ms pause before and after |
| Footnotes / citations | Skipped by default (a user setting may enable them later) |
| Parenthetical asides | Slightly lower and quicker, as an aside |
| URLs / emails | "a link to example dot com", never spelled out character by character |
| Numbers | Normalized before speaking: 1999 → "nineteen ninety-nine" (year), 3.5 → "three point five", 1/2 → "one half", $40M → "forty million dollars" |
| Abbreviations | Expanded where unambiguous: Dr. → Doctor, St. → Saint/Street from context, e.g. → "for example" |
| ALL CAPS in prose | Treated as emphasis (shouting or stress), not spelled out |
| Ellipsis `…` | A 500ms trailing pause |
| Em dash `—` | A 200ms pause (an interruption when it ends a line of dialogue) |

## 6. What the free engine can and can't do

| Direction | Kokoro (free) | OpenAI / ElevenLabs (paid, later) |
|---|---|---|
| Different voice per character | ✅ about 50 preset voices | ✅ |
| Pace, pauses, silence | ✅ speed control plus inserted silence | ✅ |
| Real emotional tone (anger, whisper, grief) | ❌ approximated through pace and pauses | ✅ through per-line instructions or audio tags |
| Emphasis on specific words | ⚠️ limited (punctuation tricks) | ✅ |
| Nonverbal sounds (sigh, laugh) | ❌ | ✅ ElevenLabs v3 |

The director **always records the full direction**, even when the current engine can't perform it. Switching to a paid engine later then needs no re-analysis: the same performance script simply renders better.

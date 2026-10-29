# Design system: "night theatre"

The app is a dark auditorium. The text is the stage, and the voice is a warm **tungsten spotlight** that moves across it. One accent color carries one meaning: *this is being spoken / this is the action.*

Tokens live in `apps/web/src/app/globals.css` (Tailwind v4 `@theme`).

## How this was derived

| Source | What we took | What we rejected, and why |
|---|---|---|
| **ui-ux-pro-max** (`--design-system`, plus `typography` and `ux` searches) | The accessibility and touch rules, the 65–75-character line length, reduced motion, the 375–1440px checks, the "book brown + page amber" palette family, and **Newsreader** (designed for long-form reading) | Its first pick was a light SaaS landing page with "AI purple + pink" and Inter, which is generic for this product |
| **frontend-design** (Anthropic) | Commit to one bold concept, a characterful display face, atmosphere (grain, spotlight), and one orchestrated page-load reveal | — |
| **high-end-visual-design** (taste-skill-classics) | The double-bezel cards, a floating island nav, button-in-button CTAs, spring easing, transform/opacity-only animation, and blur only on fixed elements | Its "never the same layout twice" rule, because a product UI needs consistency |

## Color

| Token | Hex | Use | Contrast |
|---|---|---|---|
| `stage` | `#0B0908` | Page background (warm near-black, not blue-black) | — |
| `stage-raised` | `#151210` | Card cores | — |
| `ink` | `#F4EDE2` | Primary text (parchment) | 17.1:1 on stage |
| `ink-muted` | `#A89F94` | Secondary text | 7.6:1 on stage, 7.2:1 on raised |
| `ink-faint` | `#6E665D` | **Large text only (24px+)**, such as not-yet-spoken words | 3.3:1 on raised, which passes AA for large text |
| `tungsten` | `#FFB547` | The single accent: spoken word, CTAs, focus ring, live status | 11.3:1 on stage |
| `on-tungsten` | `#1A1208` | Text on tungsten fills | 10.5:1 |
| `hairline` | ink at 8% | Borders and dividers | decorative |
| `danger` | `#F87171` | Errors and offline status | — |

The ratios were computed with the WCAG formula, not estimated.

## Type

| Role | Font | Why |
|---|---|---|
| Display (`font-display`) | **Fraunces**, light weight, with opsz and SOFT axes | Theatrical and warm; the italic gives the brand voice ("*a voice.*") |
| Reading (`font-read`) | **Newsreader**, with the opsz axis | Built for long-form reading, used for the book text in the reader |
| UI (`font-sans`) | **Geist** | A quiet, precise sans for controls |
| Labels and timecodes (`font-mono`) | **Geist Mono**, uppercase, `tracking-[0.2em]`, 10–12px | Feels like stage cues and timestamps |

All four fonts are self-hosted by `next/font`, so the page makes no requests to Google at runtime.

## Motion

- **Easing:** `ease-spring` = `cubic-bezier(0.32, 0.72, 0, 1)`. No `linear` or `ease-in-out` on UI transitions.
- **Entry:** `<Reveal>` fades content up with a blur over 0.9s, plays once, and is staggered about 0.1s on page load.
- **The voice:** `<Orb level={0..1}>` scales and glows with loudness through a spring. When idle, it breathes over a 5s cycle. A demo drives it today; the player's Web Audio `AnalyserNode` will drive it later.
- **Spoken word:** a single shared `layoutId` highlight springs from word to word. The same mechanism will power the real reader.
- **Reduced motion:** all loops and reveals are disabled, and every component renders its final state.
- **Performance:** only `transform` and `opacity` animate (plus a one-time blur on entry). `backdrop-blur` is applied only to the fixed nav, and the grain is a fixed, non-interactive layer.

## Components (`apps/web/src/components/`)

| Component | Purpose |
|---|---|
| `Bezel` | Double-bezel card: a hairline shell around a raised core with an inset top highlight |
| `PillLink` | Primary CTA: a tungsten pill with its icon nested in its own circle, at least 44px tall |
| `Nav` | Floating glass island with the wordmark, studio status and GitHub link |
| `HealthDot` | Live API/DB status (`role="status"`) |
| `Orb` | The audio-reactive "voice" |
| `HeroStage` | The orb and read-along demo, sharing one clock |
| `Reveal` | Scroll and entry fade-up |

## Pre-delivery checklist (every UI PR)

From ui-ux-pro-max, applied to this product:

- [ ] Text contrast is at least 4.5:1, or at least 3:1 only for text 24px and larger
- [ ] Visible `:focus-visible` ring (tungsten) on every interactive element
- [ ] Touch targets are at least 44×44px
- [ ] `prefers-reduced-motion` is respected
- [ ] No horizontal scroll at 375px; checked at 375, 768, 1024 and 1440px
- [ ] Reading text is at most 75 characters per line
- [ ] SVG icons only (no emoji), with thin strokes; decorative icons are `aria-hidden`
- [ ] Animations use only `transform` and `opacity`

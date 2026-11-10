# Decision log

Everything we chose, everything we tried or considered and dropped, and why — across every
session — so that months from now (or in an interview) the reasoning is still here.
Updated at every step of the November 2026 revive. Newest session at the bottom.

Status words: **Chosen** (in the product) · **Rejected** (tried or weighed, with evidence) ·
**Deferred** (worth doing later) · **Superseded** (was the plan, replaced).

---

## 1. Constraints we worked under

Many of Narrate's limits are limits of the budget and hardware, not of the design or the skills
behind it. This table says what each constraint cost and what we would do without it.

| Constraint | What it cost the product | Without it we would… |
|---|---|---|
| **$0 budget, and no payment card** for any service (re-confirmed 2026-11-10) | No hosted voice engine, no cloud GPU, no paid LLM tier, no always-on server. The app runs on the user's own computer. | Host Kokoro (or a paid voice) on a GPU server so the phone can record books anywhere; use paid LLM tiers without daily quotas. |
| **One laptop**: M1 MacBook, 16 GB, no Docker | Kokoro runs on CPU at about 2.4–2.7× real time (2 h 15 min of audio took 56 min). Two engines in parallel cost ~330 MB more for a noisy gain. | Render on a GPU, or on many CPU workers in parallel, so a whole book is ready in minutes. |
| **Free LLM tiers** | Gemini Flash free: **20 requests/day per model** (about 2 books/day). Frequent 503 "high demand" / 504 timeouts: on *All Tomorrows*, 300 of 1,053 lines fell back to default delivery. Groq free: 8,000 tokens/minute; fast but flatter acting labels. | Use a paid tier (no daily cap, fewer overload errors) for the director; batch requests; use a stronger model for acting labels. |
| **A small free voice model (Kokoro-82M)** | No emotion control: "acting" comes only from casting, pace, pauses and emphasis. | Add an expressive paid voice (OpenAI gpt-4o-mini-tts, ElevenLabs) through the existing one-file engine interface. |
| **Solo builder, short POC timeline** (built 2026-10-28 → 11-01) | No CI, no end-to-end tests, no user accounts. | Add CI, Playwright journeys, accounts. |
| **Privacy and licences** | Only DRM-free EPUBs can be read; no third-party converters for users' text; GPL tools not bundled. | (These stay, by choice.) |

---

## 2. Build session (2026-10-28 → 2026-11-01): 16 PRs

| Status | Decision | Why |
|---|---|---|
| Chosen | Free first: local **Kokoro-82M** (Apache-2.0) for voices, a free **Gemini** key for the AI director | Cost had to be ~zero. |
| Chosen | **Described personas**, never voice cloning | Ethics and law: no real people's voices. |
| Chosen | One "Performance Script" data model: sections → blocks → segments | Every stage (parse, direct, render, read) is decoupled and re-runnable. |
| Chosen | **Deterministic parsing first, AI second** | Free, instant, predictable; the AI only adds meaning. (Re-tested and re-confirmed in 2026-11 — see §3.) |
| Chosen | Plain SDKs, **no LangChain** | Linear calls, no agent loop; easier to read and debug. |
| Chosen | Render cache keyed on text + voice + speed + direction | Editing one line re-renders only that line. |
| Chosen | **Compact rows** for line labels (`12\|MARA\|anxious\|2\|fast\|…`) | Measured ~80 → ~23 output tokens per line (3.5× fewer). |
| Chosen | Gemini first for labelling, Groq as fallback (`LABEL_PROVIDER`) | Gemini follows the "~70% neutral" acting rule better; Groq is faster but flatter. |
| Chosen | ~10-minute parts for long chapters | *All Tomorrows* was one 56-minute chapter: nothing played until it was all recorded. |
| Chosen | Kokoro on **CPU, not MPS** | CPU was faster on the M1. |
| Rejected | Gemini's free **TTS** tier | About 10–100 requests/day: far too small for books. |
| Rejected | **Cerebras** | Wants bank details even for free credits. |
| Rejected | **Local LLM** for the director | An 8B model writes ~12–40 tokens/s on the M1, so directing a book would take ~17–55 min. |
| Rejected | **Rotating keys across several free accounts** | Breaks both providers' terms; limits are per account/project anyway. |
| Rejected | Pretty-printed JSON for labels | ~80 output tokens per line, even with short keys only 40% better. |
| Deferred | **Two Kokoro engines in parallel** | Averaged 4.7× vs 3.9× real time, but noisily, and costs ~330 MB more. |
| Deferred | **PWA / mobile app** | Ved deferred it on 2026-11-01. A plan existed: manifest, icons, service worker, safe-area fixes, HTTPS via Tailscale Serve, optional offline books. |
| Deferred | Paid / expressive voices | The engine interface is ready (one adapter file). |

---

## 3. Revive session 1 (2026-11-10): formatting research and the new plan

### The problem
The parser could not tell contents pages, indexes, headers, footers, page numbers and headings
from the real text. Every book and web page is formatted differently.

### What we measured (scratch experiments, real and synthetic inputs)

| Input | Narrate before the revive |
|---|---|
| Ved's Avengers paste from X (~3,300 words) | "Act One:" glued into paragraph 1 (heading followed by a single line break); "Post-Credits Scene:" read as text. |
| A Project Gutenberg book (*Sherlock Holmes*, 104k words) | **0 of 12 stories** found; cut into 69 arbitrary "Part N"; ~3,100 words of licence and the contents page read aloud. |
| A typeset book PDF (60 pages, known truth) | **0 of 611 paragraphs** right (longest 500 words), 0/3 chapters, ~half the running headers read aloud. |
| A Wikipedia article (URL import) | References + external links (~38% of words) read aloud; junk metadata became the author. |

### Options compared (same four inputs, scored against the right answer)

| Option | Result | Tokens / 60 pages | Status |
|---|---|---|---|
| **A.** AI labels every line (Gemini 3.5 Flash-Lite; Groq gpt-oss-120b) | Worst on the PDF: 478/611 paragraphs, **114 junk lines** still spoken. The AI called running headers chapter titles. On Groq's free tier a 300-page book (~200k tokens) would take ~25+ chunked minutes. | ~48k in / 3.3k out | **Rejected** |
| **B.** Rules + AI on doubtful lines only | 610/611, 7/7 headings, 0 junk — but **deleted 1 real line**. Its accuracy came from the rules; the AI layer added nothing on these inputs. | ~7–8k in | **Deferred to step 6** as an optional, guarded second opinion (see below) |
| **C.** Better deterministic rules | **611/611, 7/7, 1 junk, 0 lost** on the PDF; 100% on the others. Held-out: 12/12 Holmes stories, 0 lines lost. | 0 | **Chosen** |
| Native **EPUB import** | Prototype (~40 lines, stdlib zip + lxml already installed): 12/12 stories, title/author from metadata, licence skipped automatically. | 0 | **Chosen** |

Token cost was never the blocker: Option A would cost ~$0.09 per 100k-word book on paid
Gemini 3.5 Flash-Lite ($0.30 / $2.50 per million tokens). **Accuracy** was the blocker.
Caveat we recorded honestly: the rules were written after seeing the test inputs, so books
with unfamiliar conventions are the real risk — hence the committed harness (§4) and step 6.

### Ved's text → EPUB → import idea
**Rejected, with evidence.** The CloudConvert EPUB of the Avengers text was made by Calibre
(`calibre 8.5.0`). It had **no real headings** (only `<p>`), one page break, a contents list
with a single "Start" entry, it **dropped "&"** ("Deadpool & Wolverine" → "Deadpool  Wolverine")
and the 😱, and kept a stray `}` from the `.rtf`. An EPUB built from plain text only contains
what the converter guessed; what made it read better in Apple Books was preserved paragraph
breaks and book typography. Also: CloudConvert is a third party that receives the user's text,
and Calibre is a large GPL application. The useful idea we kept: *a cleanly structured book is
what matters* — we now get that structure ourselves, and "Export as EPUB" is a deferred feature.

### Deployment options (budget: $0, no card)

| Option | Finding | Status |
|---|---|---|
| Hugging Face Spaces, CPU Basic (2 vCPU, 16 GB) | Docker/Gradio Spaces on CPU now "require a paid plan to create" (PRO, $9/month). Disk isn't persistent. | Rejected (budget) |
| Hugging Face ZeroGPU | Gradio only; free daily GPU quota reported as 3.5–5 minutes (sources disagree, unverified). Fragile. | Rejected for now |
| Render free web service | 512 MB RAM, 0.1 CPU, sleeps after 15 min (~1 min cold start). Kokoro + PyTorch needs ~1–2 GB. Whether a card is needed is unclear. Free Postgres expires after 30 days. | Rejected for the voice engine |
| Fly.io, Oracle Cloud, Google Cloud Run, Cloudflare R2 | All need a payment card. | Rejected (no card) |
| GitHub Actions as a render backend | Free for public repos, but using Actions as an app's runtime goes against GitHub's terms. | Rejected |
| Supabase (500 MB Postgres + 1 GB storage) + Vercel + the laptop as a render worker | Workable at $0, but adds a job queue, storage layer and worker for a single user. | **Superseded** by local-first |
| Kokoro running in the phone's browser (kokoro-js, WebGPU) | Interesting truly-$0 idea; untested, battery and speed unknown. | Deferred (idea) |
| **Local-first**: anyone clones the repo and runs everything with one setup command; the phone uses the laptop over Wi-Fi (or Tailscale) | Simplest; no infra; matches "the heavy work stays on a computer". | **Chosen** (step 7) |
| **Static showcase on Vercel** (free, no card): one pre-recorded public-domain story with the real reader and player, importing disabled | Always online for interviews, no backend. | **Chosen** (step 8) |
| Live demo through a Cloudflare quick tunnel (`cloudflared tunnel --url …`) | Free, no account; but the app has no login, so the link exposes the library and the API key. Use briefly. | Allowed, for live demos only |

### AI second opinion (step 6, pending)
Ved asked to keep Option B's AI layer and offered the Claude API. Plan: off by default; runs
only when the rules look unsure (e.g. no chapters found in a long text); may only mark short
lines as heading or skip, never delete long lines; everything it skips is listed. Compare
**Claude Haiku 5.5** (`claude-haiku-5-5`, $0.10 / $0.50 per million tokens — well under a cent
per book) with Gemini Flash-Lite on the harness; keep it only if it measurably helps.
Sonnet (~20× the price) isn't needed for short-line labelling.

### Workflow change
From the revive on, **Ved makes every commit and push himself**, with no AI attribution. Claude
prepares each step, verifies it, hands over the commands and waits.

---

## 4. The revive plan (status updated per step)

| Step | What | Status |
|---|---|---|
| 1 | Structure-eval harness (`services/api/structure_eval/`, `reports/structure-eval.md`) + this log | Done 2026-11-10 |
| 2 | Text rules: glued headings, Roman numerals, "Scene:" headings, contents pages, Gutenberg licence, bylines, `***` bug, junk characters | Done 2026-11-10 |
| 3 | Web cleanup: reference sections, junk author metadata | Done 2026-11-10 |
| 4 | PDF rules: indented paragraphs, running headers on ≥3 pages, contents pages with page numbers | Planned |
| 5 | EPUB import (no new dependency) | Planned |
| 6 | Optional AI second opinion (Haiku vs Gemini), kept only if it measurably helps | Planned |
| 7 | One-command local setup, phone over Wi-Fi, verified from a fresh clone | Planned |
| 8 | Static showcase on Vercel | Planned |
| 9 | README + learning log | Planned |

**Baseline (step 1, synthetic harness, parser as of PR 16):** paragraphs exact 66.7%,
headings 14/36 (+2 extra), junk spoken 20, words lost 0, titles 4/6, authors 4/6.

**Step 2 (text rules):** paragraphs exact 66.7% → 83.3%, headings 14/36 → **36/36**, junk 20 → 4,
words lost 0 → 0. Real inputs: the Avengers paste gets its 4 acts (incl. "Post-Credits Scene:");
the full Holmes text gets all 12 stories, the right title/author and 0 licence words.

How the rules work, and why:
- **Cleanup before parsing** (`app/structure/cleanup.py`): Gutenberg START/END markers (licence
  dropped, its `Title:`/`Author:` kept as metadata); contents pages ("Contents" + its list, or ≥3
  "Title …… 12" lines). Removing junk *before* parsing means no later stage has to know about it.
- **Hard-wrapped vs one-paragraph-per-line**: if any line in a block is longer than 100
  characters, the lines are paragraphs (a paste from X/web); otherwise they're a wrapped
  paragraph and get joined (a book/Gutenberg file). Books wrap at ~60–80 characters.
- **Heading strength, two passes**: STRONG headings ("Chapter 3", "I. THE HARBOUR",
  "Post-Credits Scene:") always start chapters. WEAK ones (a short Title Case or CAPS line on its
  own, or "The First Night:") start chapters only when the text has no strong headings —
  otherwise they're sub-headings. A heading glued to its text ("Act One:\nWe open…") is split off,
  but only if it *looks* like a heading, so a wrapped line like "Part of the reason was that" isn't.
- Title Case is required for colon headings so "What he remembered afterwards:" stays text.
- A byline under the title becomes the author and is no longer spoken as a 4-word first chapter.

Known risks (accepted): a short Title Case line ending in ":" such as a letter's "Dear Sir:" can
become a sub-heading; a bare first line ("The Harbour") is taken as the book title. The PDF's
alternating running headers now appear as fake sub-headings instead of junk until step 4.

**Step 3 (web cleanup):** junk 4 → **0**, extra headings 6 → 4 (the remaining 4 are the PDF's
running headers, step 4), authors 5/6 → **6/6**. Real Wikipedia article: 1,974 → 1,212 spoken
words, i.e. the References/Sources/External links (~38%) gone and the four real sections kept.
- **Back matter** (`drop_back_matter`): in markdown, a References / Notes / Sources /
  Bibliography / External links / See also / Further reading section is dropped up to the next
  heading of the same or higher level (so a real section after it survives). In a plain paste, a
  standalone "References" line drops the rest — but only in the second half of the text, because
  near the start the word is more likely part of the story.
- **Author validation** (`clean_author`): page metadata is not trusted blindly. Names with digits,
  URLs, or words like "authority", "databases", "contributors", "Unknown" (Calibre's placeholder)
  are rejected, and the byline in the text is used instead. "By Jane Doe" → "Jane Doe".
- " - Wikipedia" is stripped from page titles.
- Housekeeping: the invisible characters in `normalize()` are now written as escapes
  (`​`…), clearing the last ruff warning in `app/structure`.

Known risk (accepted): a novel whose last chapter is literally titled "Notes" or "Sources" on a
standalone line would lose that chapter in a plain paste.

### Deferred: could be done later
PWA / phone app · paid or expressive voices · CI (GitHub Actions running the tests) · Docker
Compose (Docker isn't installed on the dev machine, so it couldn't be verified) · "Export as
EPUB" · OCR for scanned PDFs · user accounts · a real migrations tool instead of idempotent
`ALTER TABLE … ADD COLUMN IF NOT EXISTS` at startup · end-to-end tests · re-importing books made
before PRs 14/15 · fixing the pre-existing ruff warnings (FastAPI `Depends` B008).

### Dropped completely
AI labelling of every line (Option A) · converting text to EPUB through CloudConvert/Calibre ·
bundling Calibre · hosting the voice engine on free cloud tiers · rotating free API keys across
accounts · voice cloning.

---

## 5. Numbers worth remembering

| What | Number | Source |
|---|---|---|
| Kokoro speed, M1 CPU | 2.4–2.7× real time (production runs); ~3.9× in a 24-sentence spike | build session render timings |
| Time to first playable ~10-min part | ~2.5–3 min expected for real prose | PR 14 live test |
| Line labelling (director) | 560 lines in 47 s (Flash-Lite) / 120 s (Groq first) | PR 16 timed run |
| Output tokens per labelled line | ~80 (pretty JSON) → ~23 (compact rows) | PR 16 |
| Gemini Flash free tier | 20 requests/day per model | live 429 error |
| Groq free tier | 8k tokens/min, 1k requests/day, 131k context | response headers |
| Structure cleanup by AI, all lines (60-page PDF) | 47,900 in / 3,291 out tokens, 8.4 s, one request | revive experiment |
| Structure cleanup by AI, doubtful lines only | 8,217 in / 711 out (Gemini); 6,863 in / 3,460 out incl. 2,990 reasoning (Groq) | revive experiment |
| Audio size | MP3 at 64 kbps ≈ 29 MB/hour | ffmpeg settings (`-b:a 64k`) |
| Tests | 155 backend + 15 web passing (2026-11-10, before the revive changes) | pytest, node --test |

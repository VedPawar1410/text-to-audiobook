# Research notebook: data, experiments and measurements

Everything measured while building and reviving Narrate: what was tested, on which inputs, how,
the raw numbers, and what each result decided. The [decision log](../decision-log.md) records the
*decisions*; this notebook records the *evidence*. The [README](../../README.md) has the summary.

All revive measurements were taken on **2026-11-10** on Ved's M1 MacBook (16 GB), in one session.
Build-session numbers (Oct 28 – Nov 1, 2026) are marked as such and come from that session's records.

**In this folder**

| Path | What |
|---|---|
| `experiments/*.py` | The 13 experiment scripts, exactly as run (scratch quality; see [Reproduce](#12-how-to-reproduce)) |
| `data/ai-labelling/*.json` | Raw results of every AI-labelling run: the labels, token usage per request, timing, and the model's answer |
| `data/ai-labelling/tokens.md` | Token and time table for all 14 AI runs |
| `data/ai-labelling/scores-rerun-2026-11-10.txt` | The AI-vs-rules comparison, re-run from the saved results (its "narrate" row is approximate and now reflects the revived parser) |
| [`../../services/api/structure_eval/`](../../services/api/structure_eval/) | The committed evaluation harness (synthetic book, 9 formats, scorer) |
| [`../../services/api/reports/structure-eval.md`](../../services/api/reports/structure-eval.md) | Its current scores and the history of every step |

---

## 0. Index

| # | Question | Method | Answer | Section |
|---|---|---|---|---|
| E1 | How badly does the old parser handle real inputs? | Ran `parse_text` on 4 real/realistic inputs | Badly: 0/12 stories, 0/611 PDF paragraphs, licence and references read aloud | [3](#3-e1-baseline-the-old-parser-on-real-inputs) |
| E2 | Does converting text to EPUB (Ved's idea) add structure? | Unpacked the CloudConvert EPUB | No: no headings, text lost | [4](#4-e2-veds-text--epub-experiment-inspected) |
| E3 | Can AI clean up structure well and cheaply? | 4 inputs × 2 strategies × 2 providers, scored against truth | Cheap, but not better than good rules; it deleted a real line | [5](#5-e3-ai-line-labelling-vs-rules) |
| E4 | Do better rules generalise? | Held-out stories IV–XII of Holmes | 12/12 stories, 0 lines lost | [6](#6-e4-held-out-check-of-the-rules) |
| E5 | Is EPUB "structure for free"? | Prototype reader on 2 EPUBs | Yes: 12/12 stories from real headings | [7](#7-e5-epub-prototype) |
| E6 | Where can it be hosted for $0 with no card? | Web research, Nov 2026 | Nowhere for the voice engine → run locally + static showcase | [8](#8-e6-hosting-and-model-pricing-research) |
| E7 | Does the optional AI second opinion help? | Harness + hard case + real input, 2 models, 3 repeats | Yes on messy X threads only; never called on normal books | [10](#10-step-by-step-measurements) |
| E8 | Does it install for a stranger? | Fresh clone, throwaway database, bash 3.2 | After 4 fixes, yes (33 s setup) | [10](#10-step-by-step-measurements) |
| E9 | Is a PWA worth it on an iPhone? | Web research + iOS Simulator layout check; device test pending | Not yet: installed web apps may stop audio on lock; HTTPS via Tailscale first | [13](#13-e9-pwa-on-iphone-2026-11-11) |

---

## 1. Setup

| | |
|---|---|
| Machine | M1 MacBook, 16 GB, macOS (stock bash 3.2.57) |
| Stack | Next.js 16.4.3, FastAPI, Postgres 14 (Homebrew), uv, Node 24 |
| Voice | Kokoro-82M on CPU |
| LLMs used in experiments | Gemini 3.5 Flash-Lite (free key), Groq `openai/gpt-oss-120b` (free key, reasoning effort low), Claude Haiku 5.5 (`claude-haiku-5-5`, effort low) |
| Budget | $0, no payment card (Ved, 2026-11-10) |
| AI requests spent on experiments | 22 for E3, ~20 for E7, plus 2–4 for directing the showcase book |

## 2. Inputs

None of the real inputs are committed: two are third-party text, the rest are re-downloadable.

| Input | Source | Size and shape | Licence | Used for |
|---|---|---|---|---|
| **Avengers plot thread** | Copied by Ved from an X post, saved as `Avengers.txt` | 18,998 bytes, ~3,300 words, 57 newlines, 28 blank-line breaks; headings like `Act One:` followed by a *single* line break | Third-party fan text: **not committed** | E1, E3, E7 |
| **Avengers.epub** | Ved converted the text via CloudConvert (`cloudconvert.com/txt-to-epub`) | Generator `calibre (8.5.0)`; 2 spine files; 30 `<p>`, 0 headings | Third-party: not committed | E2, step 5 |
| **Stored Avengers v1** | An earlier paste in Ved's local database | 741 words, 1 section; one "paragraph" was 26 sentences / 411 words | Not committed | E1 (evidence of run-together paragraphs) |
| ***The Adventures of Sherlock Holmes*** (.txt) | [Project Gutenberg #1661](https://www.gutenberg.org/cache/epub/1661/pg1661.txt) | 607,606 bytes, CRLF; 9,630 non-blank lines, average 60.5 characters; 144 licence words before `*** START`, 2,908 after `*** END`; contents block 83 words; 12 stories as `I. A SCANDAL IN BOHEMIA`, parts as `I.` | Public domain (US) | E1, E3, E4, steps 2 & 5 |
| *Sherlock Holmes* (.epub) | [Project Gutenberg #1661](https://www.gutenberg.org/ebooks/1661.epub.noimages) | 311,635 bytes; 15 spine items, 19 TOC entries; 2,529 `<p>`, 16 `<h2>`, 3 `<h3>`; licence in `pg-header` (248 words) and `pg-footer` (2,913 words) | Public domain | E5, step 5 |
| **Holmes book PDF** (synthetic layout, real prose) | `experiments/gen_pdf.py` from stories I–III of the .txt | 60 pages, 2,478 typeset lines (64-char wrap), **611 paragraphs**, 3 story headings + 4 part markers; indented paragraphs, no blank lines; running headers alternating book title / story title; page numbers; contents page; Word-style metadata title | Public domain text | E1, E3, steps 2, 4 |
| **Wikipedia article** | [The Adventures of Sherlock Holmes](https://en.wikipedia.org/wiki/The_Adventures_of_Sherlock_Holmes), fetched through Narrate's own URL importer (trafilatura markdown) | 2,036 words, 10 headings; References / Sources / External links ≈ 38% of words; metadata title "… - Wikipedia", metadata author "Authority control databases National Spain Other MusicBrainz…" | CC BY-SA: not committed | E1, E3, step 3 |
| **How Not to Age PDF.epub** | Already in Ved's Downloads | A Calibre-split summary/quiz EPUB: 231 spine files, 217 TOC entries, 6,803 `<p>`, 932 images, 231 `<h2>`, 27 `<h3>`, 51,118 words | Copyrighted: not committed; structure counts only | E5, step 5 (messy real EPUB) |
| ***The Gift of the Magi*** | [Project Gutenberg #7256](https://www.gutenberg.org/cache/epub/7256/pg7256.txt) | 31,469 bytes; 2,057 words after cleanup | Public domain: **committed** as the showcase recording | Step 8 |
| **Synthetic harness book** | `services/api/structure_eval/corpus.py` | 40 original sentences + 6 dialogue lines, seed 7; 4 chapters, **52 paragraphs**, 2 sub-headings; ASCII, no digits | Written for the project | Steps 1–8 |

## 3. E1: baseline, the old parser on real inputs

Parser as of PR 16 (`parse_text`: markdown headings, a `CHAPTER` regex, blank-line paragraphs).

| Input | What happened | Root cause |
|---|---|---|
| Avengers paste | 3 sections; "Act One:" glued into paragraph 1 (199 words); "Post-Credits Scene:" and "TITLECARD: AVENGERS DOOMSDAY" read as paragraphs; title kept the emoji | A heading followed by a single line break was joined with its text; the chapter words didn't include "post-credits" |
| Stored Avengers v1 | One block of 26 sentences / 411 words | Lines without blank lines between them were joined |
| Holmes .txt | **0 of 12 stories found**; 69 sections named "Part 1…69"; title "The Project Gutenberg eBook of…"; author missed; ~3,050 licence words + the contents page spoken | No Roman-numeral headings, no licence or contents detection; long texts cut into ~10-minute parts |
| Holmes PDF | **0/611 paragraphs** exact; 98 blocks (longest 500 words); **0/3** chapters; running headers spoken 34 of 58; contents spoken; 22 stray numbers; title "holmes final" | Book PDFs mark paragraphs by indent, not blank lines; the alternating story-title header repeats on < 50% of pages, below the old filter's threshold |
| Wikipedia | Headings fine; References/Sources/External links spoken (681 + 23 + 58 words); author = "Authority control databases…"; stray `*` from `***bold italic***` | No back-matter rule; metadata trusted; the inline-markdown regex handled `**` and `*` but not `***` |

## 4. E2: Ved's text → EPUB experiment, inspected

Ved found the CloudConvert EPUB read better in Apple Books than the same text in Narrate, and
suggested converting every paste to EPUB first.

| Finding | Evidence |
|---|---|
| CloudConvert runs Calibre | `calibre (8.5.0)` in the package metadata |
| No real structure | 2 spine files, a contents list with one entry ("Start"); "Act One:", "Act Two:", "Post-Credits Scene:" are `<p class="calibre2">` like every other paragraph; 0 `<h1>`–`<h6>` |
| One page break | `id="calibre_pb_0"` before "Act Three" only (a bigger gap in the source) |
| **Text lost** | "Deadpool & Wolverine" → "Deadpool  Wolverine"; the 😱 dropped; a stray `}` added to the title (from the `.rtf` it was saved as) |
| Narrate on the same text | Found 3 sections with real headings, more structure than Calibre |

**Conclusion:** the EPUB step adds no structure; what read better was preserved paragraph breaks and
book typography. Rejected; native EPUB import (for real books) and better text rules instead.

## 5. E3: AI line labelling vs rules

**Question.** Can a cheap LLM label document lines (heading / junk / paragraph start) well enough to
replace or help the rules, and what does it cost?

**Inputs.** The Avengers paste, the Wikipedia markdown, the first 688 lines of the Holmes .txt
(licence + contents + story I), and the 60-page Holmes PDF's extracted text (2,780 lines with
`<<page N>>` markers). Truth per line was built from each source's known structure.

**Strategies.**
- **A, AI labels every line:** lines sent as `n|text` (capped at 100 characters); labels `H1`, `H2`,
  `P` (paragraph start), `X` (not read: headers, footers, page numbers, contents, licence,
  references), `T` title, `A` author; the model lists only lines that start something, with ranges
  for runs.
- **C, rules + AI on candidate lines only:** deterministic paragraph rules; the model sees only short
  or page-edge or numeric or CAPS lines (≤ 60 characters, ≤ 8 words) and labels H1/H2/X/T/A/K (keep).
- **R, simple rules** (Gutenberg markers, markdown headings) and **R2, better rules** (header slots,
  contents runs, isolated short headings, markdown back matter, indentation paragraphs): no AI.

**Groq's free tier** allows 8,000 tokens/minute, so inputs went in ~4.5k-token chunks a minute
apart; Strategy A on the full PDF (~48k tokens) would have needed 7+ minutes and wasn't run.

**Tokens and time** (every run, from the saved results; full table in `data/ai-labelling/tokens.md`):

| Input | Strategy | Provider | Lines sent | Tokens in / out | Time |
|---|---|---|---|---|---|
| PDF (2,780 lines) | A | Gemini | 2,654 | 47,900 / 3,291 | 8.4 s |
| PDF | C | Gemini | 642 | 8,217 / 711 | 7.3 s |
| PDF | C | Groq | 642 | 6,863 / 3,460 (2,990 reasoning) | 8.4 s, 2 requests |
| Holmes .txt head | A | Gemini | 523 | 9,687 / 765 | 9.2 s |
| Holmes .txt head | C | Gemini | 140 | 1,852 / 80 | 1.5 s |
| Wikipedia | A | Gemini | 67 | 1,979 / 76 | 4.5 s |
| Avengers | A | Gemini | 30 | 904 / 119 | 7.6 s |

**Results** (paragraphs exact; headings found (+wrong); junk lines spoken; real lines lost):

| Method | Avengers | Wikipedia | Holmes head | Holmes PDF |
|---|---|---|---|---|
| Old Narrate parser | 22/24; 2/4 | 3/9; ~10 junk | 0/3 headings; ~27 junk | **0/611**; 0/7; ~32 junk |
| R simple rules | 23/24; 0/4 | 9/9; 50 junk | 0/3; 15 junk | 567/611; 0/7; 122 junk |
| **A** AI every line (Gemini) | 24/24; 4/4 (+1) | 8/9; 1 junk | 2/3 | **478/611**; 7/7; **114 junk** |
| **C** candidates (Gemini) | 24/24; 4/4 (+2) | 9/9; 28 junk | 2/3 (+1) | 588/611; 5/7 (**+27**); 31 junk; **1 lost** |
| **C** candidates (Groq) | 24/24; 4/4 | 9/9; 50 junk | 3/3 (+1); 15 junk | 595/611; 6/7 (+13); 21 junk; **1 lost** |
| **R2** better rules | **24/24; 4/4 (+1)** | **9/9; 0 junk** | **3/3; 1 junk** | **611/611; 7/7; 1 junk; 0 lost** |
| R2 + C (Gemini or Groq) | 24/24 | 9/9 | 3/3 | 610/611; 7/7; 0 junk; **1 lost** |

**What the AI got wrong.**
- **Running headers as chapter titles.** It saw "A SCANDAL IN BOHEMIA" at the top of a page and
  called it H1 (C Gemini: 30 H1 labels for 3 real chapters).
- **Under-labelled furniture.** Strategy A Gemini marked only 7 lines X on the PDF, so 114 junk
  lines stayed.
- **Deleted real text.** Both C runs lost one real line.

**Cost.** Token cost wasn't the problem. At Gemini 3.5 Flash-Lite's paid price ($0.30 / $2.50 per
million tokens), Strategy A is ~1.9 input tokens per word, ≈ **$0.09 per 100k-word book**; Strategy
C ≈ $0.017. **Accuracy** decided it.

**Two harness bugs found and fixed during E3** (honest record):
- My first candidate filter dropped short headings that end in a lowercase letter ("Act Three",
  "## Context"), so the Wikipedia case sent only 1 line. It was fixed and C re-run (8 more requests).
- R2 first scored 567/611 on the PDF because blank lines around page breaks split paragraphs in
  *my scorer*. Ignoring blank lines next to page markers gave 611/611. Narrate's real `pdf.py` already
  joins pages without blanks.

**Caveat recorded at the time:** R2 was written after seeing these inputs, so it could be
overfitted → E4, and later the committed harness.

## 6. E4: held-out check of the rules

R2 on the **full** Holmes text, where stories IV–XII were never looked at while writing it:
**12/12** stories, 4/4 part markers, **0** false headings, 3,126 words dropped as licence/contents
(truth ≈ 3,131), **0** real lines wrongly dropped. (Narrate's old parser: 69 sections, 0 headings.)
Weakness: the unseen stories use the same conventions, so this is a weak held-out test.

## 7. E5: EPUB prototype

~40 lines using the standard zip reader and lxml (`experiments/epub_proto.py`):
- **Holmes EPUB:** title and author from metadata; **12/12** story chapters; 3,160 licence words
  skipped via `pg-header` / `pg-footer`; the contents table removed.
- **Avengers EPUB:** 1 section, 30 blocks, author "Unknown" (Calibre's placeholder). This showed
  EPUBs without headings need the text rules as a fallback.

## 8. E6: hosting and model pricing research

Researched 2026-11-10 (web search + official pages). Budget: $0, no card.

| Option | Finding | Source |
|---|---|---|
| Hugging Face Spaces, CPU Basic | 2 vCPU, 16 GB, free hardware, but "Gradio and Docker Spaces run on compute and require a paid plan to create" (PRO $9/month); disk not persistent | huggingface.co/pricing, /docs/hub/en/spaces-overview |
| Hugging Face ZeroGPU | Gradio only; daily GPU quota reported as 3.5 or 5 min free, 25 or 40 min PRO (sources disagree) | huggingface.co/docs/hub/spaces-zerogpu, forums |
| Render free web service | 512 MB RAM, 0.1 CPU, sleeps after 15 min, ~1 min cold start; 750 h/month; free Postgres expires after 30 days; whether a card is needed: sources disagree | render.com articles, third-party guides |
| Supabase free | 500 MB Postgres, 1 GB storage, pauses after 7 days idle, 2 projects | third-party summaries of supabase.com/pricing |
| Fly.io, Oracle Cloud, Google Cloud Run, Cloudflare R2 | Need a card | search results |
| Kokoro ONNX | int8 model ~92 MB (fp32 ~325 MB); fp32 ~1 GB RAM; 2–5× real time on desktop CPUs (anecdotal) | localmodel-run, Hacker News, Kokoro-FastAPI |
| Kokoro + PyTorch (ours) | The API's `.venv` is 1.0 GB | measured (`du`) |
| Gemini free-tier limits | Not listed on the docs page ("can be viewed in Google AI Studio"); RPD resets at midnight Pacific; per project | aistudio.google.com/docs/rate-limits |
| Gemini paid prices | 3.5 Flash-Lite: $0.30 in / $2.50 out per million tokens; 3.1 Flash-Lite: $0.25 / $1.50 | aistudio.google.com/docs/pricing |
| Claude prices | Haiku 5.5: $0.10 / $0.50 (prompts ≤ 100k); Sonnet 5.5: $2 / $10 | Claude API reference (cached 2026-11-03) |
| Next.js 16 dev server | Blocks pages opened from another device ("Blocked cross-origin request to Next.js dev resource") | `node_modules/next/dist/server/lib/router-utils/block-cross-site-dev.js` |

Audio storage maths: MP3 at 64 kbps ≈ 29 MB/hour, so 1 GB holds ~35 hours.

## 9. The evaluation harness

`services/api/structure_eval/`: one synthetic book (52 paragraphs, 4 chapters, 2 sub-headings, two
one-line dialogue paragraphs per chapter as heading traps) rendered into 9 formats with known truth:

| Case | Mimics |
|---|---|
| `paste_blank_lines` | the easy control |
| `paste_single_newlines` | Ved's X paste: single line breaks, "Act One:" glued to its text |
| `gutenberg_style` | licence header and footer, contents, `I. THE HARBOUR`, 70-char wrap |
| `book_pdf` | 10-page typeset PDF: indents, alternating running headers, page numbers, Word metadata title |
| `web_markdown` | trafilatura output with References / External links and a junk metadata author |
| `unusual_headings` | bare-word chapter titles next to one-line dialogue |
| `publisher_epub` | real `<h2>`/`<h3>`, nav, cover (`linear="no"`), copyright page, page-break numbers, footnote |
| `calibre_epub` | converter-made: every line a `<p>`, no headings, author "Unknown" |
| `hard_social_paste` | X thread with sentence-case titles and "Show more" / "Translate post" / "Replying to @…" / view counts |

**Metrics:** paragraphs reproduced exactly; headings found and extra; junk spoken (in non-heading
text, plus bare numbers where the book has none); words lost (story words missing); title and author.

**Sanity check of the scorer:** a perfect document scores full marks; glued, deleted and junk text are
penalised (unit tests); a naive "strip all tags" EPUB reader scores 34/52 paragraphs, 11 junk,
8 words lost on `publisher_epub`.

**History** (from `reports/structure-eval-history.json`):

| Run | Paragraphs | Headings (extra) | Junk | Lost | Titles | Authors |
|---|---|---|---|---|---|---|
| Step 1 baseline (6 cases) | 66.7% | 14/36 (+2) | 20 | 0 | 4/6 | 4/6 |
| Step 2 text rules | 83.3% | 36/36 (+6) | 4 | 0 | 5/6 | 5/6 |
| Step 3 web cleanup | 83.3% | 36/36 (+4) | 0 | 0 | 5/6 | 6/6 |
| Step 4 PDF rules | 100% | 36/36 (+0) | 0 | 0 | 6/6 | 6/6 |
| Step 5 EPUB (8 cases) | 100% | 48/48 (+0) | 0 | 0 | 8/8 | 8/8 |
| Step 6 rules only (9 cases) | 100% | 49/54 (+0) | 5 | 0 | 9/9 | 9/9 |
| Step 6 + Claude Haiku 5.5 | 100% | 53/54 (+0) | 0 | 0 | 9/9 | 9/9 |
| Step 6 + Gemini 3.5 Flash-Lite | 100% | **54/54 (+0)** | **0** | 0 | 9/9 | 9/9 |
| Step 7 per-text line-break rule | 100% | 49/54 (+0) | 5 | 0 | 9/9 | 9/9 |

## 10. Step-by-step measurements

**Step 2, text rules.** Harness as above. Real: Avengers → 4 sections (Act One 1,614 words, Act Two
1,197, Act Three 440, Post-Credits 17); Holmes .txt → 15 headings (12 stories + 3 parts), title
and author right, 0 "Gutenberg" mentions; the byline no longer a 4-word first chapter. Fixing a
test exposed that a Roman-numeral first line was taken as the book title.

**Step 3, web cleanup.** Real Wikipedia: 1,974 → **1,212** spoken words; sections Context /
Stories / Critical reception / Adaptations kept; junk author rejected; " - Wikipedia" stripped.
`clean_author` checks: "By Jane Doe" → "Jane Doe"; "Unknown", "admin", "staff 2021" rejected.

**Step 4, PDF rules.** Raw text showed the title page's title was being deleted (it doubles as the
even-page running header) and indents survived extraction. Harness PDF case → 100%. Real-prose
Holmes PDF → **610/611** paragraphs, 7/7 headings, the 2 remaining "header" mentions and the numbers
were real story text, **0 of 24,889 words lost**. The one miss is a "4½" glyph my generator garbles.
Rejected along the way: converting CAPS titles to Title Case (3 tests rely on screenplay titles in
capitals). Added: a timeline ("Born in 1901…") must not be taken for a contents page.

**Step 5, EPUB.** Real EPUBs:
- Holmes: 104,424 words, 15 headings, right title and author, 0 licence words.
- Avengers (Calibre): fell back to the text rules and found all 4 acts; author `None` ("Unknown"
  rejected).
- How Not to Age: **1,183 → 231** headings after "explicit headings switch off guessing".

Bug found: the skipped title-page `<h1>` was demoting chapter `<h2>`s. Through the web proxy, the
Holmes EPUB returned 68 sections.

**Step 6, AI second opinion.**
- **When it's called:** doubtful lines are 0 on the 8 normal harness cases, 0 on the Holmes .txt
  and .epub, 1 on the Avengers paste, and 8 on the hard case.
- **Rule fix:** "48.2K Views" and "11:42 PM" passed the Title Case test, so weak headings with
  digits were made doubtful instead.
- **Tokens per call:**

  | Call | Claude Haiku 5.5 | Gemini 3.5 Flash-Lite |
  |---|---|---|
  | Hard case, prompt v1 | 459 in / 41 out | 345 / 40 |
  | Hard case, context both sides | 668 / 41 | 499 / 40 |
  | Avengers | 266 / 5 (v1), then 326 / 5 | 240 / 2 |

- **Hard case, 3 repeated runs:** Gemini 6/6 headings every time; Claude 5/6 every time (it reads
  "The first night" as text). Junk 0 and 0 lost on every run.
- **False positive:** with prompt v1, Claude labelled the Avengers bullet "The Things fight the
  Hulk variant" a chapter title. Adding the text *before* the line fixed it for both models.
- **Cost:** ≈ $0.00007 per import on Claude Haiku 5.5.

**Step 7, fresh clone** (scratch clone at the pushed commit, throwaway database, `/bin/bash` 3.2):
- **Bug 1, lockfile drift:** `npm ci` refused: "lock file's @emnapi/wasi-threads@1.2.1 does not
  satisfy @emnapi/wasi-threads@1.2.3 … Missing: @emnapi/core@1.10.0". Fixed with
  `npm install --package-lock-only` (+71/−3 lines, optional wasm32 fallback packages only).
- **Setup:** `setup.sh` then took **33 s**, and a re-run is idempotent.
- **Bug 2, bash 3.2:** `start.sh` died with "unexpected EOF while looking for matching `''" (an
  apostrophe inside `${…:-…}`).
- **`--phone` checks:** home and /new pages 200 on the Wi-Fi address; `/api/health` through the proxy
  `{"status":"ok","database":true}`; port 8000 refused from the network.
- **Bug 3, short pasted paragraphs merged:** a paste of short one-line paragraphs lost "Act Two:".
  A per-block fix regressed the harness to 99.8% and the PDF to 595/611 (3 tests failed), so the rule
  became per-text (≥ 60% of run-on lines end with punctuation, ≥ 3 lines of evidence) and everything
  was restored.
- **Bug 4, tests read Ved's `.env`:** with `STRUCTURE_AI=gemini` they made a real call (72 s run vs
  24 s); `conftest.py` now forces it off.

**Step 8, showcase.**
- **Import:** the raw Gutenberg file gave 2,057 words, 1 section, 0 licence words, no doubtful lines.
- **Director:** ~35 s; romance; cast Narrator (am_fenrir), Della (af_heart), Madame Sofronie
  (af_bella), Jim (am_michael); 129 lines (Narrator 107, Della 14, Sofronie 4, Jim 4); emotions:
  warm 36, neutral 19, playful 14, tender 12, weary 8, melancholic 7.
- **Recording:** **192 s for 714.2 s of audio (3.7× real time)**.
- **Snapshot:** 5.6 MB (MP3 5,581 KB, manifest 113 KB, document 47 KB).
- **Local demo build with the API stopped:** all pages 200, reads 200, audio range 206, unknown
  book 404.
- **Live on Vercel:** pages in 0.2–1.3 s, the full MP3 (5,714,541 bytes) in 1.7 s, no console
  errors; after the button change, the homepage button opens the reader.

## 11. Build-session numbers (Oct 28 – Nov 1, 2026)

| What | Number | Source |
|---|---|---|
| Kokoro speed on M1 CPU | 2.4–2.7× real time in production runs; ~3.9× in a 24-sentence spike; two engines in parallel 4.7× vs 3.9× but noisy, +~330 MB | render timings, PR 3 / PR 14 spikes |
| *All Tomorrows* (PDF, 17,065 words) | 2 h 15 min of audio in 56 min; one 56-minute chapter before PR 14; title "Microsoft Word - All Tomorrows.doc" before PR 15 | build session |
| Directing *All Tomorrows* | ~7 min; 300 of 1,053 lines on default delivery after failed batches (before PR 14's retry pass) | build session |
| Gemini Flash free tier | 20 requests/day per model (live 429: `limit: 20 … requests per day`) ≈ 2 books/day | build session |
| Output tokens per labelled line | ~80 (pretty JSON) → ~23 (compact rows): 13,150 output tokens for 560 lines, 47 s on Flash-Lite | PR 16 |
| Groq free tier | 8,000 tokens/min, 1,000 requests/day, 131k context; 0.4–4 s; flatter labels (e.g. "tender" on 360 of 560 lines once) | response headers, PR 16 |
| Local LLM director | an 8B model at ~12–40 tokens/s on the M1 → ~17–55 min per book (rejected) | build session |
| Time to first playable part | ~2.5–3 min expected for real prose (86 s on repetitive test text) | PR 14 |
| Tests at the end of the build | 155 backend (1 skipped) + 15 web | 2026-11-01 |

## 12. How to reproduce

The experiment scripts take a working folder (`S`) with the inputs in fixed sub-folders. Run them
from `services/api` so they can import the app:

```bash
S=/tmp/narrate-research; mkdir -p $S/dl_gutenberg $S/pdf_holmes $S/web $S/ai
curl -sSL -o $S/dl_gutenberg/holmes.txt https://www.gutenberg.org/cache/epub/1661/pg1661.txt
curl -sSL -o $S/dl_gutenberg/holmes.epub https://www.gutenberg.org/ebooks/1661.epub.noimages
tr -d '\r' < $S/dl_gutenberg/holmes.txt > $S/dl_gutenberg/holmes_lf.txt
cd services/api
uv run --no-sync python ../../docs/research/experiments/gen_pdf.py $S/dl_gutenberg/holmes_lf.txt $S/pdf_holmes
PYTHONPATH=. uv run --no-sync python ../../docs/research/experiments/score_holmes_pdf.py $S/pdf_holmes
PYTHONPATH=. uv run --no-sync python ../../docs/research/experiments/heldout.py $S
```

- `build_inputs.py` builds the numbered-line inputs for E3. The Wikipedia text comes from Narrate's
  URL importer; the Avengers case runs only if `AVENGERS_TXT` points at your own copy.
- `label_exp.py <S> <case> <A|C> <gemini|groq>` makes real API calls with the keys in
  `services/api/.env`; `score_ai.py <S>` scores the saved runs.
- Exact numbers can differ slightly from re-runs: LLM answers vary, and the scripts import the
  *current* parser.
- The committed harness needs no downloads: `uv run --no-sync python -m structure_eval`.

## 13. E9: PWA on iPhone (2026-11-11)

**Question.** Should Narrate become an installable web app (PWA) for Ved's iPhone?

**Research** (web search; full table and sources in the [decision log §6](../decision-log.md)):
- **Background audio:** installed iOS web apps are reported to stop audio on lock or backgrounding,
  with flaky lock-screen controls (WebKit bug 198277, Apple forums 762582, iOS 26 reports). A
  Safari tab keeps playing.
- **Offline storage:** Safari evicts a site's data after 7 days of Safari use without a visit;
  home-screen apps are exempt (~60% of disk quota per MDN).
- **HTTPS:** Tailscale Serve provides it with automatic certificates, reachable from the tailnet only.

**P1 measurements:**
- **Production build:** `<link rel="apple-touch-icon" href="/apple-icon?…" sizes="180x180">` on
  every page, and `<meta name="viewport" content="…, viewport-fit=cover">`.
- **Generated icon:** a PNG, 180 × 180, RGBA (the orb on `#0b0908`).
- **iOS Simulator** (iPhone 17 created for this, iOS 27.2 runtime, Safari): the nav clears the
  Dynamic Island; the player bar sits above Safari's floating toolbar.
- **`start.sh`:** bash 3.2 syntax OK; `--tailscale` without Tailscale prints "Tailscale isn't
  installed…" and exits 1; an unknown option prints the usage line and exits 1.
- **Not yet measured:** the real Tailscale run (Tailscale isn't installed yet) and anything about
  locked-screen audio. That needs Ved's physical iPhone (P2); the simulator can't answer it.
- **Tailscale run (after Ved installed it):** the first run printed a consent link to enable Serve,
  then served the tailnet-only HTTPS address; the page loaded on the iPhone on Wi-Fi and on mobile
  data; `tailscale serve status` showed the proxy to `http://127.0.0.1:3000` as "tailnet only".
- **P2 instrument:** `apps/web/src/app/lab/lock-test` measures seconds locked vs seconds of audio
  played per lock, plus display mode and storage quota; results go in this section when Ved runs it.

**P2 results, round 1** (Ved's iPhone, iOS 27.0.1 by Safari version; 2026-11-11, on the `/lab/lock-test` page):

| Running as | Locked | Audio played | Still playing on return | Lock-screen taps | Reading |
|---|---|---|---|---|---|
| Safari tab | 20 s | 17 s | yes | pause, play | Played throughout; the ~3 s gap is the pause/play |
| Safari tab | 85 s | 25 s | no | pause | Stopped because Ved paused it from the lock screen, not by iOS |
| Installed web app | 19 s | 17 s | yes | pause, play | Played while locked, **contrary to the reports** in the research above |

Both modes: storage quota **41.2 GB**, persisted `false`, Media Session available. The lock screen showed
the orb artwork and working play/pause in both. Skip and scrubbing were unavailable, as expected on the
test page (it registers only play and pause); the real reader had no scrubbing or time skips either, so
it now registers `seekbackward`, `seekforward` (15 s) and `seekto` instead of sentence-jump track buttons.

**Limits of round 1:** the installed-app result is a single 19-second run. Still to measure: a lock of
several minutes, and moving to the next chapter while locked.

**P2 results, round 2** (same iPhone, **installed web app**, the real reader, reported by Ved):

| Test | Result |
|---|---|
| Next chapter while locked (*Lock Test Two Chapters*, 32 s + 33 s) | Carried on into Chapter Two by itself |
| Lock of at least 5 minutes, untouched (*The Gift of the Magi*) | Kept playing |
| Lock-screen 15-second skips | Work |
| Lock-screen progress bar | Drags and seeks |

**Conclusion of E9:** on this iPhone (iOS 27.0.1), an installed web app keeps audio playing while locked,
contrary to the older reports (2020 to iOS 26). One device and one iOS version; the measurement is what
decided P3, not the reports.

**P3.2 offline audio, simulator run** (iPhone 17 simulator, iOS 27.2, real WebKit; `/lab/offline-test`). The book
(*The Gift of the Magi*, 5.7 MB) was saved, then the server was stopped so the site had no network behind it:

| Method | Played to | Seek to 357 s landed at | Audio requests seen by the service worker |
|---|---|---|---|
| Saved file through the service worker | 3.9 s | 359.9 s | 2 |
| From memory (blob URL) | 3.9 s | 359.8 s | 0 |

So iOS does route media through the service worker, and the byte-range answers work. The page reported
"online" because only this site was down, not the whole network. The embedded browser pane couldn't register
a service worker at all, so the simulator was used instead. A real iPhone in airplane mode is still to be tested.

**P3.2 on the real iPhone, airplane mode** (`online: false`; installed app; 5.7 MB saved):

| Method | Played to | Seek to 357 s landed at | Error | Requests through the service worker |
|---|---|---|---|---|
| Saved file through the service worker | 3.7 s | 359.4 s | none | 2 (`bytes=0-1`, then `bytes=0-5714540`) |
| From memory (blob URL) | 3.7 s | 359.4 s | none | 0 |

iOS probes with a 2-byte range, then asks for the whole file; both are answered from the cache. Ved also heard
both play.

**P3.3 "Save for offline", real iPhone, airplane mode** (installed app; two-chapter test book; saved from the app,
reader opened before going offline). These are Ved's observations, not timed measurements:

| Check | Result |
|---|---|
| Plays with word highlighting | Yes |
| Moves to Chapter Two by itself | Yes |
| Progress bar | Works |
| Tapping a word jumps there | Works |
| Remove puts the button back to "Save for offline" | Yes |

Not covered by this run: opening the app from scratch offline (P3.4), a full-length book, the lock screen while offline.

**P3.4 offline launch, simulator run** (iPhone 17 simulator, iOS 27.2, real WebKit, Safari killed before each launch;
production build on a separate port; two-chapter test book):

| Scenario | Result |
|---|---|
| Online, after saving | Library shows all 3 books; the saved one is marked "On this phone" |
| Server stopped (connection refused), cold launch | Library opens, correct fonts, only the saved book, explanation shown |
| Tap the book, then Play | Reader opens; audio ran to 0:17 with word highlighting |
| Tap "New" (a page never saved) | Lands on the Library |
| Server frozen with SIGSTOP (accepts connections, never answers: stands in for a sleeping Mac), cold launch | Saved Library appeared, seen between 14 and 21 s after launch, including the simulator's slow Safari start (not timed precisely) |
| Server unfrozen with the page still open | The full 3-book list replaced the saved one by itself |

Saved app code is whatever the pages' HTML lists (17 files for the Library); the whole build is 1.8 MB.

**P3.4 on the real iPhone** (installed app, two-chapter test book). Ved's observations, not timed measurements:

| Check | Result |
|---|---|
| Library marks the saved book "On this phone" | Yes |
| Airplane mode, app swiped away, opened from the icon | Library appears with the saved book |
| Play | Word highlighting; moves to Chapter Two by itself |
| Lock the phone while playing offline | Keeps playing; lock-screen skip and scrub work |
| Ask, offline | Shows the "Can't reach Narrate" message |
| Network on, Narrate stopped on the Mac (Ctrl-C), app reopened | Saved Library appears in "a fraction of a second" |
| Narrate restarted, app reopened | All books back |

The stopped-server case was fast because an awake Mac refuses the connection at once. A Mac really asleep with
Tailscale on wasn't tried on the phone, only simulated above. A full-length book offline is also still untested.

# text-to-audiobook

Turn any long text (scripts, articles, books, PDFs) into an expressive, multi-voice audiobook, with a read-along reader that highlights each word as it's spoken.

> **Status:** early POC, built in small reviewable PRs.

## What it does (v1 goals)

- **AI director.** Reads your text and works out its structure (chapters, scenes, dialogue), genre and tone, who is speaking, and how each line should be performed.
- **A cast of voices.** Each character gets its own voice. You can design voice *personas* by describing them ("gravelly, menacing, slow and theatrical"). Real people's voices are never cloned.
- **Read-along.** Live word highlighting synced to the audio. Click any word to jump there, or turn highlighting off.
- **Ask the AI.** Pause, select a passage and ask what it means, without leaving the page.
- **Export.** Download MP3 per chapter, or a single M4B audiobook with chapter markers.
- **No length limit.** Paste text, upload `.txt`/`.md`/PDF, or point it at a web article.

## Cost model

Free by default:

- **Narration:** [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M), running locally (Apache-2.0).
- **AI director and Q&A:** a free Gemini API key that you bring yourself.
- **Paid voice engines** (OpenAI, ElevenLabs) are planned as optional upgrades.

## Stack

| Layer | Tech |
|---|---|
| Web | Next.js (App Router) · TypeScript · Tailwind · Motion |
| API | Python · FastAPI · SQLAlchemy |
| Data | Postgres (local) · audio files on disk |
| AI | Kokoro TTS (local) · Gemini / Claude / OpenAI via your own API key |

## Repo layout

```
apps/web/        Next.js frontend
services/api/    FastAPI backend (ingest → structure → director → render → export)
docs/            design system, narration guide
```

## Design skills

The UI is built with these Claude Code skills. They are installed locally under `.claude/skills/`, which is git-ignored:

- [frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design)
- [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- [high-end-visual-design](https://github.com/Leonxlnx/taste-skill-classics)

## License

MIT

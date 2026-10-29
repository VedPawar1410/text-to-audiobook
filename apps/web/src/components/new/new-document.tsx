"use client";

import { useRouter } from "next/navigation";
import { useState, type DragEvent, type FormEvent } from "react";
import { Bezel } from "@/components/bezel";
import { PillButton, SECONDARY } from "@/components/pill-link";
import { ErrorNote, Eyebrow, LABEL } from "@/components/ui";
import { api, type ParsedDocument } from "@/lib/api";
import { formatDuration, titleCase } from "@/lib/vocabulary";

type Source = "paste" | "file" | "link";

const SOURCES: { id: Source; label: string }[] = [
  { id: "paste", label: "Paste" },
  { id: "file", label: "File" },
  { id: "link", label: "Link" },
];

const ACCEPT = ".txt,.md,.markdown,.pdf";

/** Pick a source → the API parses it → preview → save and start the director. */
export function NewDocument() {
  const router = useRouter();
  const [source, setSource] = useState<Source>("paste");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState<"reading" | "saving" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [parsed, setParsed] = useState<ParsedDocument | null>(null);
  const [title, setTitle] = useState("");

  async function read(load: () => Promise<ParsedDocument>) {
    setBusy("reading");
    setError(null);
    try {
      const document = await load();
      setParsed(document);
      setTitle(document.title ?? "");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  function pickFile(picked: File | undefined) {
    if (!picked) return;
    setFile(picked);
    read(() => api.ingestFile(picked));
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    pickFile(event.dataTransfer.files[0]);
  }

  function submit(event: FormEvent, load: () => Promise<ParsedDocument>) {
    event.preventDefault();
    read(load);
  }

  async function direct() {
    if (!parsed) return;
    setBusy("saving");
    setError(null);
    try {
      const saved = await api.saveDocument({ ...parsed, title: title.trim() || parsed.title });
      // If starting the director fails (e.g. no API key), the notes page shows why and offers a retry
      await api.direct(saved.id).catch(() => undefined);
      router.push(`/documents/${saved.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  }

  if (parsed) {
    return (
      <div className="flex flex-col gap-6">
        <Preview parsed={parsed} title={title} onTitle={setTitle} />
        <div className="flex flex-wrap items-center gap-2">
          <PillButton onClick={direct} busy={busy === "saving"}>
            Direct it
          </PillButton>
          <button type="button" className={SECONDARY} onClick={() => setParsed(null)}>
            Start over
          </button>
        </div>
        {error && <ErrorNote>{error}</ErrorNote>}
      </div>
    );
  }

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;

  return (
    <div className="flex flex-col gap-6">
      <div role="group" aria-label="Where is your text?" className="inline-flex w-fit rounded-full border border-hairline p-1">
        {SOURCES.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            aria-pressed={source === id}
            onClick={() => {
              setSource(id);
              setError(null);
            }}
            className={`min-h-11 cursor-pointer rounded-full px-5 text-sm transition-colors duration-300 ease-spring ${
              source === id ? "bg-ink text-stage" : "text-ink-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <Bezel>
        <div className="p-3 md:p-5">
          {source === "paste" && (
            <form onSubmit={(e) => submit(e, () => api.ingestText(text))} className="flex flex-col gap-3">
              <label htmlFor="paste" className="sr-only">
                Your text
              </label>
              <textarea
                id="paste"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste a script, a chapter, an article…"
                className="min-h-[45vh] w-full resize-y rounded-[1.25rem] bg-transparent p-4 font-read text-lg leading-relaxed text-ink placeholder:text-ink-faint"
              />
              <div className="flex flex-wrap items-center justify-between gap-4 border-t border-hairline px-2 pt-4">
                <p className="font-mono text-xs text-ink-muted">
                  {text.length.toLocaleString()} characters · {words.toLocaleString()} words
                </p>
                <PillButton type="submit" busy={busy === "reading"} disabled={!text.trim()}>
                  Read it
                </PillButton>
              </div>
            </form>
          )}

          {source === "file" && (
            <label
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={`flex min-h-[45vh] cursor-pointer flex-col items-center justify-center gap-4 rounded-[1.25rem] border border-dashed p-8 text-center transition-colors duration-300 ease-spring ${
                dragging ? "border-tungsten bg-tungsten/5" : "border-hairline"
              }`}
            >
              <input
                type="file"
                accept={ACCEPT}
                className="peer sr-only"
                onChange={(e) => pickFile(e.target.files?.[0])}
              />
              <span className="font-display text-2xl md:text-3xl">Drop a file here</span>
              <span className="text-ink-muted">.txt, .md or .pdf, up to 25 MB</span>
              {/* Dragging is never the only way: the picker works by click or keyboard */}
              <span className="min-h-11 rounded-full border border-hairline px-5 py-2.5 text-sm transition-colors peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-tungsten hover:border-ink/30">
                {busy === "reading" ? "Reading…" : "Choose a file"}
              </span>
              {file && (
                <span className="font-mono text-xs text-ink-muted">
                  {file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB
                </span>
              )}
            </label>
          )}

          {source === "link" && (
            <form
              onSubmit={(e) => submit(e, () => api.ingestUrl(url.trim()))}
              className="flex min-h-[30vh] flex-col justify-center gap-4 p-4"
            >
              <label htmlFor="url" className="font-display text-2xl md:text-3xl">
                Paste a link to an article
              </label>
              <input
                id="url"
                type="url"
                inputMode="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://"
                className="min-h-12 w-full rounded-2xl border border-hairline bg-stage px-4 font-mono text-sm text-ink placeholder:text-ink-faint"
              />
              <p className="text-sm text-ink-muted">
                Works with most articles and Wikipedia. For a post on X, copy its text and use Paste.
              </p>
              <div>
                <PillButton type="submit" busy={busy === "reading"} disabled={!url.trim()}>
                  Read it
                </PillButton>
              </div>
            </form>
          )}
        </div>
      </Bezel>

      {error && <ErrorNote>{error}</ErrorNote>}
    </div>
  );
}

function Preview({ parsed, title, onTitle }: { parsed: ParsedDocument; title: string; onTitle: (t: string) => void }) {
  const { stats } = parsed;
  const named = parsed.sections.filter((s) => s.title);
  const stat = (label: string, value: string) => (
    <div>
      <dt className={LABEL}>{label}</dt>
      <dd className="mt-2 font-display text-2xl md:text-3xl">{value}</dd>
    </div>
  );

  return (
    <Bezel>
      <div className="flex flex-col gap-10 p-6 md:p-10">
        <div>
          <Eyebrow>{parsed.format === "screenplay" ? "Screenplay" : "Prose"} · ready for the director</Eyebrow>
          <label htmlFor="title" className="sr-only">
            Title
          </label>
          {/* A textarea so long titles wrap; field-sizing grows it to fit its text */}
          <textarea
            id="title"
            rows={1}
            value={title}
            onChange={(e) => onTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && e.preventDefault()}
            placeholder="Untitled"
            className="mt-4 w-full resize-none rounded-lg bg-transparent font-display text-3xl leading-[1.1] font-light tracking-tight text-ink [field-sizing:content] placeholder:text-ink-faint supports-[field-sizing:content]:overflow-hidden md:text-5xl"
          />
        </div>

        <dl className="grid grid-cols-2 gap-6 md:grid-cols-4">
          {stat("Listening time", formatDuration(stats.estimated_minutes))}
          {stat("Words", stats.words.toLocaleString())}
          {stat("Sentences", stats.sentences.toLocaleString())}
          {stat(parsed.format === "screenplay" ? "Scenes" : "Sections", String(named.length || parsed.sections.length))}
        </dl>

        {stats.speakers.length > 0 && (
          <div>
            <h2 className={LABEL}>Speakers found</h2>
            <ul className="mt-3 flex flex-wrap gap-2">
              {stats.speakers.slice(0, 16).map((speaker) => (
                <li key={speaker} className="rounded-full border border-hairline px-4 py-2 text-sm">
                  {titleCase(speaker)}
                </li>
              ))}
              {stats.speakers.length > 16 && (
                <li className="px-2 py-2 text-sm text-ink-muted">+{stats.speakers.length - 16} more</li>
              )}
            </ul>
          </div>
        )}

        {named.length > 1 && (
          <div>
            <h2 className={LABEL}>{parsed.format === "screenplay" ? "Scenes" : "Sections"}</h2>
            <ol className="mt-3 grid gap-x-8 gap-y-2 text-ink-muted md:grid-cols-2">
              {named.slice(0, 8).map((section, i) => (
                <li key={i} className="truncate">
                  {section.title}
                </li>
              ))}
              {named.length > 8 && <li>+{named.length - 8} more</li>}
            </ol>
          </div>
        )}
      </div>
    </Bezel>
  );
}

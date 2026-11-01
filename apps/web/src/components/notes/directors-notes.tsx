"use client";

import { type KeyboardEvent, use, useEffect, useState } from "react";
import { Bezel } from "@/components/bezel";
import { PillButton } from "@/components/pill-link";
import { ErrorNote, Eyebrow, LABEL, Skeleton } from "@/components/ui";
import { api, type DocumentDetail, type Persona, type Segment } from "@/lib/api";
import { useDocument } from "@/lib/hooks";
import { formatDuration, genreLabel } from "@/lib/vocabulary";
import { CastSection } from "./cast-card";
import { DirectingState } from "./directing-state";
import { RenderPanel } from "./render-panel";
import { ScriptView } from "./script-view";

export function DirectorsNotes({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { document, setDocument, error, reload } = useDocument(id);
  // Bumped on every cast or line edit, so the audiobook panel re-checks what's stale
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (document) window.document.title = `${document.title ?? "Untitled"} · Narrate`;
  }, [document]);

  if (error && !document) return <ErrorNote>{error}</ErrorNote>;
  if (!document) return <NotesSkeleton />;

  const replacePersona = (persona: Persona) => {
    setRevision((r) => r + 1);
    setDocument((d) => d && { ...d, personas: d.personas.map((p) => (p.cast_id === persona.cast_id ? persona : p)) });
  };

  const replaceSegment = (segment: Segment) => {
    setRevision((r) => r + 1);
    setDocument(
      (d) =>
        d && {
          ...d,
          sections: d.sections.map((s) => ({
            ...s,
            segments: s.segments.map((g) => (g.id === segment.id ? segment : g)),
          })),
        },
    );
  };

  return (
    <article className="flex flex-col gap-14">
      <Header document={document} onSaved={(saved) => setDocument((d) => d && { ...d, title: saved.title, author: saved.author })} />

      {document.status === "directing" && <DirectingState progress={document.progress} sentences={document.stats.sentences} />}

      {(document.status === "parsed" || document.status === "failed") && (
        <StartDirecting document={document} onStarted={reload} />
      )}

      {document.status === "directed" && (
        <>
          {document.warning && <p className="rounded-2xl border border-hairline px-4 py-3 text-sm text-ink-muted">{document.warning}</p>}
          <Overview document={document} />
          <RenderPanel document={document} revision={revision} />
          <CastSection document={document} onChange={replacePersona} />
          <ScriptView document={document} onChange={replaceSegment} />
        </>
      )}
    </article>
  );
}

type Saved = { title: string | null; author: string | null };

// Inline fields that look like text until hovered or focused; Enter or leaving the field saves
const INLINE =
  "rounded-lg bg-transparent transition-colors duration-300 ease-spring hover:bg-ink/[0.04] focus:bg-ink/[0.04] focus:outline-none focus-visible:ring-1 focus-visible:ring-tungsten/60 disabled:hover:bg-transparent";

function Header({ document, onSaved }: { document: DocumentDetail; onSaved: (saved: Saved) => void }) {
  const [title, setTitle] = useState(document.title ?? "");
  const [author, setAuthor] = useState(document.author ?? "");
  const [error, setError] = useState<string | null>(null);
  const { stats } = document;
  const locked = document.status === "directing";

  // A document reloaded with a new author (the director found one) updates the field
  const [seenAuthor, setSeenAuthor] = useState(document.author);
  if (document.author !== seenAuthor) {
    setSeenAuthor(document.author);
    setAuthor(document.author ?? "");
  }

  async function save(patch: { title?: string; author?: string }) {
    try {
      const saved = await api.updateDocument(document.id, patch);
      onSaved({ title: saved.title, author: saved.author });
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function saveTitle() {
    const next = title.trim();
    if (!next || next === document.title) return setTitle(document.title ?? "");
    void save({ title: next });
  }

  function saveAuthor() {
    const next = author.trim();
    setAuthor(next);
    if (next !== (document.author ?? "")) void save({ author: next });
  }

  const enterSaves = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    e.currentTarget.blur();
  };

  return (
    <header>
      <Eyebrow>
        {document.format === "screenplay" ? "Screenplay" : "Prose"}
        {document.genre && ` · ${genreLabel(document.genre)}`}
      </Eyebrow>
      <label htmlFor="document-title" className="sr-only">
        Title
      </label>
      {/* A textarea so long titles wrap; field-sizing grows it to fit */}
      <textarea
        id="document-title"
        rows={1}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={saveTitle}
        onKeyDown={enterSaves}
        disabled={locked}
        placeholder="Untitled"
        title="Click to rename"
        aria-describedby={error ? "title-error" : undefined}
        className={`${INLINE} mt-5 -ml-2 w-[calc(100%+0.5rem)] resize-none px-2 font-display text-4xl leading-[1.05] font-light tracking-tight text-ink [field-sizing:content] placeholder:text-ink-faint supports-[field-sizing:content]:overflow-hidden md:text-6xl`}
      />
      <div className="mt-2 flex items-baseline gap-2 font-read text-xl text-ink-muted italic md:text-2xl">
        <span aria-hidden className={author ? "" : "text-ink-faint"}>
          by
        </span>
        <label htmlFor="document-author" className="sr-only">
          Author
        </label>
        <input
          id="document-author"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          onBlur={saveAuthor}
          onKeyDown={enterSaves}
          disabled={locked}
          placeholder="add the author"
          maxLength={200}
          className={`${INLINE} min-w-[10ch] px-1.5 py-0.5 text-ink-muted [field-sizing:content] placeholder:text-ink-faint`}
        />
      </div>
      {error && (
        <p id="title-error" role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
      <p className="mt-4 font-mono text-xs text-ink-muted">
        {formatDuration(stats.estimated_minutes)} · {stats.words.toLocaleString()} words ·{" "}
        {stats.sentences.toLocaleString()} lines
      </p>
    </header>
  );
}

function StartDirecting({ document, onStarted }: { document: DocumentDetail; onStarted: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const failed = document.status === "failed";

  async function start() {
    setBusy(true);
    setError(null);
    try {
      await api.direct(document.id);
      onStarted();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Bezel>
      <div className="flex flex-col gap-6 p-8 md:p-12">
        <h2 className="font-display text-3xl tracking-tight">
          {failed ? "The director couldn't finish." : "Ready for the director."}
        </h2>
        <p className="max-w-xl leading-relaxed text-ink-muted">
          {failed
            ? document.error
            : "It will read the whole text, decide the genre, cast a voice for every role, and direct each line."}
        </p>
        <div>
          <PillButton onClick={start} busy={busy}>
            {failed ? "Try again" : "Direct it"}
          </PillButton>
        </div>
        {error && <ErrorNote>{error}</ErrorNote>}
      </div>
    </Bezel>
  );
}

function Overview({ document }: { document: DocumentDetail }) {
  return (
    <section aria-labelledby="overview" className="grid gap-10 md:grid-cols-12">
      <div className="md:col-span-7">
        <h2 id="overview" className={LABEL}>
          The director&apos;s read
        </h2>
        <p className="mt-4 font-read text-xl leading-relaxed md:text-2xl">{document.summary}</p>
      </div>
      <dl className="flex flex-col gap-6 md:col-span-5 md:border-l md:border-hairline md:pl-10">
        <div>
          <dt className={LABEL}>Genre</dt>
          <dd className="mt-2 text-lg">
            {genreLabel(document.genre)}
            {document.subgenre && <span className="text-ink-muted"> · {document.subgenre}</span>}
          </dd>
        </div>
        <div>
          <dt className={LABEL}>Narration</dt>
          <dd className="mt-2 leading-relaxed text-ink-muted">{document.narrator_style}</dd>
        </div>
      </dl>
    </section>
  );
}

export function NotesSkeleton() {
  return (
    <div className="flex flex-col gap-8" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-16 w-2/3" />
      <Skeleton className="h-48" />
      <div className="grid gap-6 md:grid-cols-3">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

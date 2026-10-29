"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bezel } from "@/components/bezel";
import { PillLink } from "@/components/pill-link";
import { ErrorNote, Skeleton } from "@/components/ui";
import { api, type DocumentSummary, type Status } from "@/lib/api";
import { formatDuration, genreLabel } from "@/lib/vocabulary";

const STATUS: Record<Status, { label: string; dot: string }> = {
  parsed: { label: "Not directed yet", dot: "bg-ink-faint" },
  directing: { label: "Directing…", dot: "animate-pulse bg-tungsten" },
  directed: { label: "Directed", dot: "bg-tungsten" },
  failed: { label: "Needs another try", dot: "bg-danger" },
};

export function Library() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch((e: Error) => setError(e.message));
  }, []);

  async function remove(document: DocumentSummary) {
    if (!window.confirm(`Delete “${document.title ?? "Untitled"}”? This can't be undone.`)) return;
    try {
      await api.remove(document.id);
      setDocuments((all) => all?.filter((d) => d.id !== document.id) ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error && !documents) return <ErrorNote>{error}</ErrorNote>;
  if (!documents) {
    return (
      <div className="grid gap-6 md:grid-cols-2" aria-busy="true" aria-label="Loading">
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <Bezel>
        <div className="flex flex-col items-start gap-6 p-8 md:p-12">
          <p className="font-display text-3xl tracking-tight">Nothing here yet.</p>
          <p className="max-w-md text-ink-muted">Bring your first text and the director will take it from there.</p>
          <PillLink href="/new" icon="right">
            Start a new book
          </PillLink>
        </div>
      </Bezel>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {error && <ErrorNote>{error}</ErrorNote>}
      <ul className="grid gap-6 md:grid-cols-2">
        {documents.map((document) => {
          const status = STATUS[document.status];
          return (
            <li key={document.id}>
              <Bezel className="h-full">
                {/* The title link stretches over the card; the delete button sits above it */}
                <div className="relative flex h-full flex-col gap-6 p-6 transition-colors duration-300 ease-spring hover:bg-ink/[0.02]">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="font-mono text-[11px] tracking-[0.2em] text-ink-muted uppercase">
                        {document.format === "screenplay" ? "Screenplay" : "Prose"}
                        {document.genre && ` · ${genreLabel(document.genre)}`}
                      </p>
                      <h2 className="mt-2 font-display text-2xl tracking-tight">
                        <Link href={`/documents/${document.id}`} className="after:absolute after:inset-0 after:rounded-[calc(2rem-0.375rem)]">
                          {document.title ?? "Untitled"}
                        </Link>
                      </h2>
                    </div>
                    <button
                      type="button"
                      onClick={() => remove(document)}
                      aria-label={`Delete ${document.title ?? "Untitled"}`}
                      className="relative z-10 flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-danger/10 hover:text-danger"
                    >
                      <svg aria-hidden viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.25">
                        <path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.6 8.5h5.8l.6-8.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                  <div className="mt-auto flex flex-wrap items-center justify-between gap-3 text-sm text-ink-muted">
                    <span className="flex items-center gap-2">
                      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />
                      {status.label}
                    </span>
                    <span className="font-mono text-xs">
                      {formatDuration(document.stats.estimated_minutes)} · {document.stats.words.toLocaleString()} words
                    </span>
                  </div>
                </div>
              </Bezel>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

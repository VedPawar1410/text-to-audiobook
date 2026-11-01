"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Bezel } from "@/components/bezel";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { PillLink, SECONDARY } from "@/components/pill-link";
import { ErrorNote, Skeleton } from "@/components/ui";
import { api, type DocumentSummary, type Status } from "@/lib/api";
import { formatDuration, genreLabel } from "@/lib/vocabulary";

const STATUS: Record<Status, { label: string; dot: string }> = {
  parsed: { label: "Not directed yet", dot: "bg-ink-faint" },
  directing: { label: "Directing…", dot: "animate-pulse bg-tungsten" },
  directed: { label: "Directed", dot: "bg-tungsten" },
  failed: { label: "Needs another try", dot: "bg-danger" },
};

const SHOWN_IN_DIALOG = 5;

function titleOf(document: DocumentSummary) {
  return document.title ?? "Untitled";
}

function books(count: number) {
  return count === 1 ? "1 book" : `${count} books`;
}

export function Library() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<DocumentSummary[] | null>(null); // awaiting confirmation
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch((e: Error) => setError(e.message));
  }, []);

  // Escape leaves select mode (while the dialog is open, Escape closes only the dialog)
  useEffect(() => {
    if (!selecting || pending) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setSelecting(false);
      setSelected(new Set());
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selecting, pending]);

  function stopSelecting() {
    setSelecting(false);
    setSelected(new Set());
  }

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }

  async function confirmDelete() {
    if (!pending) return;
    setDeleting(true);
    setError(null);
    // One request per book, in parallel: one failure (say, a book still rendering) doesn't stop the rest
    const results = await Promise.allSettled(pending.map((d) => api.remove(d.id)));
    const deleted = new Set(pending.filter((_, i) => results[i].status === "fulfilled").map((d) => d.id));
    const failed = pending.filter((d) => !deleted.has(d.id));

    setDocuments((all) => all?.filter((d) => !deleted.has(d.id)) ?? null);
    setSelected((current) => new Set([...current].filter((id) => !deleted.has(id))));
    if (failed.length) {
      const reason = (results.find((r) => r.status === "rejected") as PromiseRejectedResult).reason as Error;
      setError(`Couldn't delete ${failed.map(titleOf).join(", ")}: ${reason.message}`);
    } else if (selecting) {
      stopSelecting();
    }
    setDeleting(false);
    setPending(null);
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

  const allSelected = selected.size === documents.length;
  const count = pending?.length ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex min-h-11 flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-ink-muted" aria-live="polite">
          {selecting ? `${selected.size} selected` : books(documents.length)}
        </p>
        <div className="flex gap-1">
          {selecting ? (
            <>
              <button
                type="button"
                onClick={() => setSelected(allSelected ? new Set() : new Set(documents.map((d) => d.id)))}
                className={SECONDARY}
              >
                {allSelected ? "Clear" : "Select all"}
              </button>
              <button type="button" onClick={stopSelecting} className={`${SECONDARY} text-ink`}>
                Done
              </button>
            </>
          ) : (
            <button type="button" onClick={() => setSelecting(true)} className={SECONDARY}>
              Select
            </button>
          )}
        </div>
      </div>

      {error && <ErrorNote>{error}</ErrorNote>}

      <ul className={`grid gap-6 md:grid-cols-2 ${selecting ? "pb-24" : ""}`}>
        {documents.map((document) => (
          <li key={document.id}>
            <BookCard
              document={document}
              selecting={selecting}
              selected={selected.has(document.id)}
              onToggle={() => toggle(document.id)}
              onDelete={() => setPending([document])}
            />
          </li>
        ))}
      </ul>

      <AnimatePresence>
        {selecting && selected.size > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}
            className="fixed inset-x-0 bottom-0 z-30 flex justify-center px-3 pb-3 md:pb-6"
          >
            <div className="flex items-center gap-4 rounded-full border border-hairline bg-stage/85 py-1.5 pr-1.5 pl-6 backdrop-blur-xl">
              <span className="text-sm text-ink-muted">{books(selected.size)}</span>
              <button
                type="button"
                onClick={() => setPending(documents.filter((d) => selected.has(d.id)))}
                className="inline-flex min-h-11 cursor-pointer items-center rounded-full bg-danger px-5 text-sm font-medium text-stage transition-transform duration-300 ease-spring active:scale-[0.98]"
              >
                Delete
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <ConfirmDialog
        open={pending !== null}
        title={count === 1 && pending ? `Delete “${titleOf(pending[0])}”?` : `Delete ${books(count)}?`}
        confirmLabel={count === 1 ? "Delete book" : `Delete ${books(count)}`}
        busyLabel="Deleting…"
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPending(null)}
      >
        {pending && count > 1 && (
          <ul className="mb-3 flex flex-col gap-1 text-ink">
            {pending.slice(0, SHOWN_IN_DIALOG).map((d) => (
              <li key={d.id} className="truncate">
                {titleOf(d)}
              </li>
            ))}
            {count > SHOWN_IN_DIALOG && <li className="text-ink-muted">and {count - SHOWN_IN_DIALOG} more</li>}
          </ul>
        )}
        <p>The text, cast and recorded audio are removed for good. This can&apos;t be undone.</p>
      </ConfirmDialog>
    </div>
  );
}

type BookCardProps = {
  document: DocumentSummary;
  selecting: boolean;
  selected: boolean;
  onToggle: () => void;
  onDelete: () => void;
};

function BookCard({ document, selecting, selected, onToggle, onDelete }: BookCardProps) {
  const status = STATUS[document.status];
  const title = titleOf(document);
  const pickId = `pick-${document.id}`;
  // The title (a link, or in select mode the checkbox's label) stretches over the whole card
  const stretch = "after:absolute after:inset-0 after:rounded-[calc(2rem-0.375rem)]";

  return (
    <Bezel className={`h-full transition-shadow duration-300 ease-spring ${selected ? "ring-1 ring-tungsten/60" : ""}`}>
      <div
        className={`relative flex h-full flex-col gap-6 rounded-[calc(2rem-0.375rem)] p-6 transition-colors duration-300 ease-spring ${
          selected ? "bg-tungsten/[0.05]" : "hover:bg-ink/[0.02]"
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="font-mono text-[11px] tracking-[0.2em] text-ink-muted uppercase">
              {document.format === "screenplay" ? "Screenplay" : "Prose"}
              {document.genre && ` · ${genreLabel(document.genre)}`}
            </p>
            <h2 className="mt-2 font-display text-2xl tracking-tight">
              {selecting ? (
                <label htmlFor={pickId} className={`cursor-pointer ${stretch}`}>
                  {title}
                </label>
              ) : (
                <Link href={`/documents/${document.id}`} className={stretch}>
                  {title}
                </Link>
              )}
            </h2>
          </div>
          {selecting ? (
            <span className="relative z-10 flex h-11 w-11 shrink-0 items-center justify-center">
              <input
                id={pickId}
                type="checkbox"
                checked={selected}
                onChange={onToggle}
                aria-label={`Select ${title}`}
                className="peer h-6 w-6 cursor-pointer appearance-none rounded-full border border-ink/30 transition-colors duration-300 ease-spring checked:border-tungsten checked:bg-tungsten"
              />
              <svg
                aria-hidden
                viewBox="0 0 16 16"
                className="pointer-events-none absolute h-3.5 w-3.5 text-on-tungsten opacity-0 peer-checked:opacity-100"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M3.5 8.5 6.5 11.5 12.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          ) : (
            <button
              type="button"
              onClick={onDelete}
              aria-label={`Delete ${title}`}
              className="relative z-10 flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-danger/10 hover:text-danger"
            >
              <svg aria-hidden viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.25">
                <path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.6 8.5h5.8l.6-8.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          )}
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
  );
}

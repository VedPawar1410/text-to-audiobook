"use client";

import { useEffect, useState } from "react";
import { SECONDARY } from "@/components/pill-link";
import type { Chapter } from "@/lib/api";
import { offlineState, offlineSupported, removeBook, saveBook, type OfflineState } from "@/lib/offline";
import { estimateBytes, formatSize } from "@/lib/offline-urls";

/** Download this book to the phone so it plays with no connection. */
export function SaveOffline({ documentId, chapters }: { documentId: string; chapters: Chapter[] }) {
  const [state, setState] = useState<OfflineState | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const complete = chapters.length > 0 && chapters.every((c) => c.status === "ready" && !c.stale);

  useEffect(() => {
    let live = true;
    if (offlineSupported()) {
      void offlineState(documentId, chapters).then((next) => {
        if (live) setState(next);
      });
    }
    return () => {
      live = false;
    };
  }, [documentId, chapters]);

  // Plain http (the --phone mode) has no Cache Storage; an unfinished book isn't worth saving
  if (!state || !complete) return null;

  async function save() {
    setError(null);
    setProgress(0);
    try {
      const bytes = await saveBook(documentId, chapters, (done, total) => setProgress(Math.round((done / total) * 100)));
      setState({ kind: "saved", bytes });
    } catch (e) {
      setError((e as Error).message);
      setState({ kind: "none" });
    } finally {
      setProgress(null);
    }
  }

  async function remove() {
    await removeBook(documentId);
    setState({ kind: "none" });
  }

  return (
    <div className="mt-2 -ml-5 flex flex-wrap items-center gap-x-1 text-sm text-ink-muted" aria-live="polite">
      {progress !== null ? (
        <span className="px-5 py-2">Saving… {progress}%</span>
      ) : state.kind === "saved" ? (
        <>
          <span className="px-5 py-2">✓ Saved for offline · {formatSize(state.bytes)}</span>
          <button type="button" onClick={() => void remove()} className={SECONDARY}>
            Remove
          </button>
        </>
      ) : (
        <>
          <button type="button" onClick={() => void save()} className={SECONDARY}>
            ↓ Save for offline (about {formatSize(estimateBytes(chapters))})
          </button>
          {state.kind === "stale" && <span className="px-5 py-2">The saved copy is out of date or was cleared.</span>}
        </>
      )}
      {error && <span className="px-5 py-2 text-danger">{error}</span>}
    </div>
  );
}

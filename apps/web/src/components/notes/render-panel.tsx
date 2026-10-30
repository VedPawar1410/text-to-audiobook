"use client";

import { useState } from "react";
import { Bezel } from "@/components/bezel";
import { PillButton, PillLink, SECONDARY } from "@/components/pill-link";
import { ErrorNote, LABEL } from "@/components/ui";
import { api, chapterAudioUrl, exportUrl, isRendering, type Chapter, type DocumentDetail, type ExportFormat } from "@/lib/api";
import { useRender } from "@/lib/hooks";
import { formatDuration } from "@/lib/vocabulary";

const REALTIME_FACTOR = 2.5; // Kokoro on an M1 CPU renders ~2.5x faster than real time (PR 3)
const M4B_SECONDS_PER_HOUR = 14; // AAC encoding speed on an M1 (PR 10)

function clock(seconds: number) {
  const s = Math.round(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const rest = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${rest}` : `${m}:${rest}`;
}

export function RenderPanel({ document, revision }: { document: DocumentDetail; revision: number }) {
  const { status, reload } = useRender(document.id, revision);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!status) return null;

  const { job, chapters } = status;
  const rendering = isRendering(job);
  const ready = chapters.filter((c) => c.status === "ready");
  const stale = chapters.filter((c) => c.stale).length;
  const complete = chapters.length > 0 && ready.length === chapters.length && stale === 0;
  const percent = job?.total_lines ? Math.round((job.done_lines / job.total_lines) * 100) : 0;
  const total = ready.reduce((sum, c) => sum + (c.duration_s ?? 0), 0);

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const label = stale
    ? `Re-record ${stale} changed ${stale === 1 ? "chapter" : "chapters"}`
    : ready.length
      ? "Finish rendering"
      : "Render audiobook";
  const hint = ready.length
    ? "Only lines that changed are recorded again."
    : `About ${formatDuration(document.stats.estimated_minutes / REALTIME_FACTOR)} on this machine. Chapters play as soon as they're ready.`;

  return (
    <section aria-labelledby="audio-heading">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 id="audio-heading" className="font-display text-3xl tracking-tight md:text-4xl">
          The audiobook
        </h2>
        {ready.length > 0 && (
          <p className="font-mono text-xs text-ink-muted">
            {ready.length} of {chapters.length} chapters · {clock(total)}
          </p>
        )}
      </div>

      <Bezel className="mt-8">
        <div className="flex flex-col gap-6 p-6 md:p-8">
          {rendering && job ? (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p>
                  Recording… <span className="font-mono text-sm text-ink-muted">{job.done_lines.toLocaleString()} of {job.total_lines.toLocaleString()} lines</span>
                </p>
                <button
                  type="button"
                  onClick={() => act(() => api.cancelRender(document.id))}
                  className="min-h-11 cursor-pointer rounded-full px-4 text-sm text-ink-muted hover:bg-hairline hover:text-ink"
                >
                  Cancel
                </button>
              </div>
              <div
                role="progressbar"
                aria-label="Rendering progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percent}
                className="h-1.5 overflow-hidden rounded-full bg-ink/10"
              >
                <div className="h-full rounded-full bg-tungsten transition-[width] duration-700 ease-spring" style={{ width: `${percent}%` }} />
              </div>
              <p className="text-sm text-ink-muted">Chapters become playable as soon as they&apos;re ready. You can leave this page.</p>
            </div>
          ) : complete ? (
            <p className="text-ink-muted">Every chapter is recorded and up to date.</p>
          ) : (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <PillButton onClick={() => act(() => api.startRender(document.id))} busy={busy}>
                {label}
              </PillButton>
              <p className="max-w-md text-sm text-ink-muted">{hint}</p>
            </div>
          )}

          {ready.length > 0 && (
            <div>
              <PillLink href={`/documents/${document.id}/listen`} icon="right">
                Open the reader
              </PillLink>
            </div>
          )}

          {!rendering && chapters.length > 0 && ready.length === chapters.length && (
            <Downloads documentId={document.id} seconds={total} stale={stale} />
          )}

          {job?.status === "failed" && job.error && <ErrorNote>{job.error}</ErrorNote>}
          {error && <ErrorNote>{error}</ErrorNote>}

          {chapters.length > 0 && (
            <ol className="flex flex-col divide-y divide-hairline border-t border-hairline">
              {chapters.map((chapter) => (
                <ChapterRow key={chapter.section_id} documentId={document.id} chapter={chapter} />
              ))}
            </ol>
          )}
        </div>
      </Bezel>
    </section>
  );
}

function Downloads({ documentId, seconds, stale }: { documentId: string; seconds: number; stale: number }) {
  const [preparing, setPreparing] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wait = Math.round((seconds / 3600) * M4B_SECONDS_PER_HOUR);

  async function download(format: ExportFormat) {
    setPreparing(format);
    setError(null);
    try {
      await api.prepareExport(documentId, format);
      // The file is ready, so this answers at once; its attachment header keeps us on the page
      const link = window.document.createElement("a");
      link.href = exportUrl(documentId, format);
      link.click();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPreparing(null);
    }
  }

  return (
    <div className="flex flex-col gap-3 border-t border-hairline pt-6">
      <p className={LABEL}>Take it with you</p>
      <div className="flex flex-wrap items-center gap-2">
        <PillButton icon="down" onClick={() => void download("m4b")} busy={preparing === "m4b"} disabled={preparing !== null}>
          Download audiobook
        </PillButton>
        <button type="button" onClick={() => void download("mp3")} disabled={preparing !== null} className={SECONDARY}>
          {preparing === "mp3" ? "Packaging…" : "Single MP3"}
        </button>
      </div>
      <p aria-live="polite" className="max-w-md text-sm text-ink-muted">
        {preparing === "m4b"
          ? `Packaging with chapter markers…${wait > 10 ? ` About ${wait < 60 ? `${wait} seconds` : formatDuration(wait / 60)}.` : ""}`
          : "M4B keeps the chapters in Apple Books and most audiobook apps. MP3 plays anywhere."}
        {stale > 0 && " Changed chapters download as they were last recorded."}
      </p>
      {error && <ErrorNote>{error}</ErrorNote>}
    </div>
  );
}

function ChapterRow({ documentId, chapter }: { documentId: string; chapter: Chapter }) {
  const state = chapter.stale
    ? "Changed since recording"
    : chapter.status === "ready"
      ? clock(chapter.duration_s ?? 0)
      : chapter.status === "rendering"
        ? "Recording…"
        : "Not recorded yet";

  return (
    <li className="grid gap-3 py-4 md:grid-cols-[1fr_auto] md:items-center">
      <div className="flex min-w-0 items-baseline gap-3">
        <span className={`${LABEL} shrink-0`}>{String(chapter.position + 1).padStart(2, "0")}</span>
        <span className="truncate">{chapter.title ?? "Opening"}</span>
        <span className={`shrink-0 font-mono text-xs ${chapter.stale ? "text-tungsten" : "text-ink-muted"}`}>{state}</span>
      </div>
      {chapter.status === "ready" && (
        // Native controls for now; the read-along player arrives in PR 8
        <audio
          controls
          preload="none"
          src={chapterAudioUrl(documentId, chapter)}
          aria-label={`Play ${chapter.title ?? "opening"}`}
          className="h-11 w-full md:w-80"
        />
      )}
    </li>
  );
}

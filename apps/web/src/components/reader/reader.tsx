"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo } from "react";
import { Bezel } from "@/components/bezel";
import { PillLink, SECONDARY } from "@/components/pill-link";
import { ErrorNote, Eyebrow, Skeleton } from "@/components/ui";
import type { Chapter, DocumentDetail } from "@/lib/api";
import { useDocument, useRender } from "@/lib/hooks";
import { useReadAlong } from "@/lib/use-read-along";
import { PlayerBar } from "./player-bar";
import { ReaderText } from "./reader-text";

export function Reader({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { document, error } = useDocument(id);
  const { status } = useRender(id, 0);

  if (error && !document) return <ErrorNote>{error}</ErrorNote>;
  if (!document || !status) return <ReaderSkeleton />;

  if (!status.chapters.some((c) => c.status === "ready")) {
    return (
      <Bezel>
        <div className="flex flex-col items-start gap-6 p-8 md:p-12">
          <p className="font-display text-3xl tracking-tight">Nothing to listen to yet.</p>
          <p className="max-w-md text-ink-muted">Direct the text and render the audiobook, then come back to read along.</p>
          <PillLink href={`/documents/${id}`} icon="right">
            Go to the director&apos;s notes
          </PillLink>
        </div>
      </Bezel>
    );
  }

  return <ReadAlongView document={document} chapters={status.chapters} />;
}

function ReadAlongView({ document, chapters }: { document: DocumentDetail; chapters: Chapter[] }) {
  const player = useReadAlong(document, chapters);
  const { toggle, step, setHighlight, highlight, seekTo } = player;

  const playable = useMemo(() => new Set(player.ready.map((c) => c.section_id)), [player.ready]);
  const names = useMemo(
    () => Object.fromEntries(document.personas.map((p) => [p.cast_id, p.display_name])),
    [document.personas],
  );
  const onSeek = useCallback((segmentId: number, wordIndex: number) => void seekTo(segmentId, wordIndex), [seekTo]);

  useEffect(() => {
    window.document.title = `${document.title ?? "Untitled"} · Read along`;
  }, [document.title]);

  // Space plays and pauses, arrows move by sentence, H toggles the highlight
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      // Leave keys alone in form controls and buttons (Space on a focused button presses it)
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest("input, textarea, select, button, [contenteditable='true']")) return;
      if (event.key === " ") {
        event.preventDefault();
        toggle();
      } else if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        void step(event.key === "ArrowRight" ? 1 : -1);
      } else if (event.key.toLowerCase() === "h") {
        setHighlight(!highlight);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle, step, setHighlight, highlight]);

  return (
    <>
      <header className="mx-auto max-w-[44rem]">
        <Eyebrow>Read along</Eyebrow>
        <h1 className="mt-5 font-display text-4xl leading-[1.05] font-light tracking-tight md:text-6xl">
          {document.title ?? "Untitled"}
        </h1>
        <p className="mt-4 text-sm text-ink-muted">
          {player.resumed && "Picking up where you left off. "}Tap any word to hear it from there.
          <span className="hidden md:inline"> Space plays and pauses, ← → move by sentence.</span>
        </p>
        <Link href={`/documents/${document.id}`} className={`${SECONDARY} mt-3 -ml-5`}>
          ← Director&apos;s notes
        </Link>
      </header>

      <ReaderText document={document} playable={playable} names={names} highlight={highlight} onSeek={onSeek} />

      {!player.following && player.playing && (
        <button
          type="button"
          onClick={player.follow}
          className="fixed bottom-36 left-1/2 z-30 min-h-11 -translate-x-1/2 cursor-pointer rounded-full border border-hairline bg-stage/90 px-5 text-sm backdrop-blur-xl md:bottom-40"
        >
          ↓ Follow the voice
        </button>
      )}

      <PlayerBar player={player} />
    </>
  );
}

export function ReaderSkeleton() {
  return (
    <div className="mx-auto flex max-w-[44rem] flex-col gap-6" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-16 w-2/3" />
      <Skeleton className="h-40" />
      <Skeleton className="h-40" />
    </div>
  );
}

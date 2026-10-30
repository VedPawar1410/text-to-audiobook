"use client";

import { Fragment, memo, type MouseEvent } from "react";
import type { DocumentDetail, Segment } from "@/lib/api";
import { groupBlocks } from "@/lib/blocks";
import { displayWords } from "@/lib/timing";

type Props = {
  document: DocumentDetail;
  playable: Set<number>; // section ids with recorded audio
  names: Record<string, string>;
  highlight: boolean;
  onSeek: (segmentId: number, wordIndex: number) => void;
};

/**
 * The book's text, rendered once. Every word has an id the player can find, and
 * one delegated click handler (not one per word) turns any word into a seek target.
 * Memoised: playback state changes must never re-render this.
 */
export const ReaderText = memo(function ReaderText({ document, playable, names, highlight, onSeek }: Props) {
  function onClick(event: MouseEvent<HTMLDivElement>) {
    if (!window.getSelection()?.isCollapsed) return; // the reader is selecting text, not seeking
    const target = event.target as HTMLElement;
    const segment = target.closest<HTMLElement>("[data-seg]");
    if (!segment?.closest(".playable")) return;
    const word = target.closest<HTMLElement>("[data-word]");
    onSeek(Number(segment.dataset.seg), word ? Number(word.dataset.word) : -1);
  }

  return (
    <div onClick={onClick} className={`read-along mx-auto mt-14 flex max-w-[44rem] flex-col gap-16 ${highlight ? "" : "highlight-off"}`}>
      {document.sections.map((section) => {
        const recorded = playable.has(section.id);
        return (
          <section
            key={section.id}
            className={`flex flex-col gap-6 [contain-intrinsic-size:auto_1200px] [content-visibility:auto] ${recorded ? "playable" : "opacity-60"}`}
          >
            {!recorded && <p className="font-mono text-xs text-ink-muted">Not recorded yet</p>}
            {groupBlocks(section.segments).map((block) => (
              <Block key={block[0].id} block={block} names={names} />
            ))}
          </section>
        );
      })}
    </div>
  );
});

const READING = "font-read text-xl leading-[1.75] md:text-2xl";

function Block({ block, names }: { block: Segment[]; names: Record<string, string> }) {
  const first = block[0];
  const lines = block.map((segment) => <Line key={segment.id} segment={segment} />);

  switch (first.block_kind) {
    case "scene_break":
      return <p aria-hidden className="py-2 text-center tracking-[1em] text-ink-faint">· · ·</p>;
    case "heading":
      return <h2 className="font-display text-3xl tracking-tight md:text-4xl">{lines}</h2>;
    case "scene_heading":
      return <p className="font-mono text-sm tracking-[0.15em] uppercase">{lines}</p>;
    case "transition":
      return <p className="text-right font-mono text-sm tracking-[0.15em] uppercase">{lines}</p>;
    case "quote":
      return <blockquote className={`${READING} border-l border-hairline pl-6 italic`}>{lines}</blockquote>;
    case "dialogue":
      return (
        <div className="md:pl-10">
          <p className="mb-1 font-mono text-xs tracking-[0.2em] text-tungsten uppercase">
            {names[first.role] ?? first.role}
            {first.block_direction && <span className="ml-2 tracking-normal text-ink-muted normal-case">({first.block_direction})</span>}
          </p>
          <p className={READING}>{lines}</p>
        </div>
      );
    default:
      return <p className={READING}>{lines}</p>;
  }
}

function Line({ segment }: { segment: Segment }) {
  const words = displayWords(segment.text);
  return (
    <span id={`seg-${segment.id}`} data-seg={segment.id} className="seg">
      {words.map((word, i) => (
        <Fragment key={i}>
          <span id={`w-${segment.id}-${i}`} data-word={i} className="word">
            {word}
          </span>
          {i < words.length - 1 && " "}
        </Fragment>
      ))}{" "}
    </span>
  );
}

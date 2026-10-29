"use client";

import { useState } from "react";
import { LABEL } from "@/components/ui";
import { api, type DocumentDetail, type Segment } from "@/lib/api";
import { EMOTIONS } from "@/lib/vocabulary";

type Props = { document: DocumentDetail; onChange: (segment: Segment) => void };

/** Consecutive segments of the same block (a paragraph, one character's speech…). */
function groupBlocks(segments: Segment[]): Segment[][] {
  const blocks: Segment[][] = [];
  for (const segment of segments) {
    const current = blocks.at(-1);
    if (current && current[0].block_index === segment.block_index) current.push(segment);
    else blocks.push([segment]);
  }
  return blocks;
}

export function ScriptView({ document, onChange }: Props) {
  const [editing, setEditing] = useState<number | null>(null);
  const names = Object.fromEntries(document.personas.map((p) => [p.cast_id, p.display_name]));

  return (
    <section aria-labelledby="script-heading">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 id="script-heading" className="font-display text-3xl tracking-tight md:text-4xl">
          The performance
        </h2>
        <p className="max-w-sm text-sm text-ink-muted">
          Every line, as the director will have it read. Tap a delivery to change it.
        </p>
      </div>

      <div className="mt-10 flex flex-col gap-16">
        {document.sections.map((section) => (
          // Long scripts: let the browser skip layout for chapters that are off-screen
          <div key={section.id} className="flex flex-col gap-6 [contain-intrinsic-size:auto_900px] [content-visibility:auto]">
            {groupBlocks(section.segments).map((block) => (
              <Block
                key={block[0].id}
                block={block}
                names={names}
                documentId={document.id}
                editing={editing}
                setEditing={setEditing}
                onChange={onChange}
              />
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

type BlockProps = {
  block: Segment[];
  names: Record<string, string>;
  documentId: string;
  editing: number | null;
  setEditing: (id: number | null) => void;
  onChange: (segment: Segment) => void;
};

function Block({ block, names, ...rest }: BlockProps) {
  const first = block[0];

  if (first.block_kind === "scene_break") {
    return (
      <p aria-label="Scene break" className="py-4 text-center tracking-[1em] text-ink-faint">
        · · ·
      </p>
    );
  }

  const rows = block.map((segment) => <Line key={segment.id} segment={segment} names={names} {...rest} />);

  if (first.block_kind === "dialogue") {
    return (
      <div className="md:pl-16">
        <p className="mb-1 font-mono text-xs tracking-[0.2em] text-tungsten uppercase md:pl-[10.5rem]">
          {names[first.role] ?? first.role}
          {first.block_direction && <span className="ml-2 tracking-normal text-ink-muted normal-case">({first.block_direction})</span>}
        </p>
        {rows}
      </div>
    );
  }

  return <div>{rows}</div>;
}

const TEXT_STYLE: Record<string, string> = {
  heading: "font-display text-2xl tracking-tight md:text-3xl",
  scene_heading: "font-mono text-sm tracking-[0.15em] uppercase",
  transition: "font-mono text-sm tracking-[0.15em] text-ink-muted uppercase md:text-right",
  quote: "font-read text-lg italic leading-relaxed text-ink-muted",
};

function Line({ segment, names, documentId, editing, setEditing, onChange }: { segment: Segment } & Omit<BlockProps, "block">) {
  const isEditing = editing === segment.id;
  // In prose, the director can give a quoted line to a character: show who
  const voicedBy = segment.block_kind !== "dialogue" && segment.role !== "NARRATOR" ? names[segment.role] : null;

  return (
    <div className="grid gap-2 py-1.5 md:grid-cols-[9rem_1fr] md:gap-6">
      <div className={isEditing ? "md:col-span-2" : ""}>
        {isEditing ? (
          <DeliveryEditor segment={segment} documentId={documentId} onChange={onChange} onDone={() => setEditing(null)} />
        ) : (
          <DeliveryChip segment={segment} onEdit={() => setEditing(segment.id)} />
        )}
      </div>
      <p className={`${TEXT_STYLE[segment.block_kind] ?? "font-read text-lg leading-relaxed"} ${isEditing ? "md:col-start-2" : ""}`}>
        {voicedBy && <span className="mr-2 font-mono text-xs tracking-[0.2em] text-tungsten uppercase">{voicedBy}</span>}
        <Emphasised text={segment.text} words={segment.emphasis} />
      </p>
    </div>
  );
}

function Dots({ intensity }: { intensity: number }) {
  return (
    <span aria-hidden className="flex gap-0.5">
      {[1, 2, 3].map((n) => (
        <span key={n} className={`h-1 w-1 rounded-full ${n <= intensity ? "bg-tungsten" : "bg-ink/20"}`} />
      ))}
    </span>
  );
}

function DeliveryChip({ segment, onEdit }: { segment: Segment; onEdit: () => void }) {
  return (
    <button
      type="button"
      onClick={onEdit}
      aria-label={`${segment.emotion}, intensity ${segment.intensity} of 3. Change delivery`}
      // 32px to look like a chip; the ::after extends the touch target to 44px
      className="relative inline-flex h-8 cursor-pointer items-center gap-2 rounded-full border border-hairline px-3 font-mono text-[11px] text-ink-muted transition-colors duration-300 ease-spring after:absolute after:-inset-1.5 hover:border-tungsten/50 hover:text-ink"
    >
      {segment.emotion}
      <Dots intensity={segment.intensity} />
    </button>
  );
}

type EditorProps = { segment: Segment; documentId: string; onChange: (s: Segment) => void; onDone: () => void };

function DeliveryEditor({ segment, documentId, onChange, onDone }: EditorProps) {
  const [error, setError] = useState<string | null>(null);

  async function save(patch: Partial<Pick<Segment, "emotion" | "intensity">>) {
    setError(null);
    try {
      onChange(await api.updateSegment(documentId, segment.id, patch));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div
      role="group"
      aria-label="Change delivery"
      onKeyDown={(e) => e.key === "Escape" && onDone()}
      className="flex flex-wrap items-center gap-3 rounded-2xl border border-tungsten/40 bg-stage-raised p-2"
    >
      <label className="flex items-center gap-2">
        <span className={LABEL}>Emotion</span>
        <select
          autoFocus
          value={segment.emotion}
          onChange={(e) => save({ emotion: e.target.value })}
          className="min-h-11 cursor-pointer rounded-full border border-hairline bg-stage px-3 font-mono text-xs text-ink"
        >
          {EMOTIONS.map((emotion) => (
            <option key={emotion} value={emotion}>
              {emotion}
            </option>
          ))}
        </select>
      </label>
      <div role="group" aria-label="Intensity" className="flex items-center gap-1">
        <span className={`${LABEL} mr-1`}>Intensity</span>
        {[1, 2, 3].map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={segment.intensity === n}
            onClick={() => save({ intensity: n })}
            className={`h-11 w-11 cursor-pointer rounded-full font-mono text-xs transition-colors ${
              segment.intensity === n ? "bg-tungsten text-on-tungsten" : "text-ink-muted hover:bg-hairline"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      <button type="button" onClick={onDone} className="ml-auto min-h-11 cursor-pointer rounded-full px-4 text-sm text-ink-muted hover:text-ink">
        Done
      </button>
      {error && (
        <p role="alert" className="w-full px-2 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

/** The director's emphasis, shown as a dotted underline. */
function Emphasised({ text, words }: { text: string; words: string[] }) {
  if (!words.length) return <>{text}</>;
  const stressed = new Set(words.map((w) => w.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "")));
  return (
    <>
      {text.split(/(\s+)/).map((part, i) =>
        stressed.has(part.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "")) ? (
          <span key={i} className="underline decoration-tungsten/70 decoration-dotted decoration-2 underline-offset-[6px]">
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </>
  );
}

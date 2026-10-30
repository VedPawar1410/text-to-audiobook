"use client";

import type { CSSProperties, ReactNode } from "react";
import { Orb } from "@/components/orb";
import { formatClock } from "@/lib/timing";
import { SPEEDS, type ReadAlong } from "@/lib/use-read-along";

const ICON_BUTTON =
  "flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-muted transition-colors duration-300 ease-spring hover:bg-hairline hover:text-ink";

function Icon({ d, fill = false }: { d: string; fill?: boolean }) {
  return (
    <svg aria-hidden viewBox="0 0 16 16" className="h-4 w-4" fill={fill ? "currentColor" : "none"} stroke={fill ? "none" : "currentColor"} strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

const PREVIOUS = "M4 3.5v9M12.5 3.5 6 8l6.5 4.5z";
const NEXT = "M12 3.5v9M3.5 3.5 10 8l-6.5 4.5z";
const PLAY = "M5 3.5v9l7.5-4.5z";
const PAUSE = "M5 3.5h2v9H5zM9 3.5h2v9H9z";
const HIGHLIGHT = "M2.5 13.5h11M4 10.5l5.5-7 3 2.5-5.5 7H4z";
const ASK = "M2.5 4.5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v4.5a2 2 0 0 1-2 2H7l-3 2.5v-2.5h0a1.5 1.5 0 0 1-1.5-1.5z";

function Chip({ children }: { children: ReactNode }) {
  return <span className="font-mono text-[11px] text-ink-muted">{children}</span>;
}

/** Fixed glass bar: scrubber, chapter, transport, speed and highlight. */
export function PlayerBar({ player, onAsk }: { player: ReadAlong; onAsk: () => void }) {
  const { chapter, ready, playing, time, duration } = player;
  const progress = duration ? (Math.min(time, duration) / duration) * 100 : 0;

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 px-3 pb-3 md:px-6 md:pb-6">
      <div className="mx-auto flex max-w-4xl flex-col gap-1 rounded-[1.75rem] border border-hairline bg-stage/85 px-3 pt-1 pb-2 backdrop-blur-xl md:px-5 md:pb-3">
        <input
          type="range"
          aria-label="Position in chapter"
          aria-valuetext={`${formatClock(time)} of ${formatClock(duration)}`}
          min={0}
          max={duration || 0}
          step={0.1}
          value={Math.min(time, duration || 0)}
          onChange={(e) => player.seek(Number(e.target.value))}
          className="scrubber h-11 w-full"
          style={{ "--progress": `${progress}%` } as CSSProperties}
        />
        {/* Phones: chapter and time get their own row above the controls */}
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 sm:flex-nowrap md:gap-3">
          <Orb level={player.level} className="hidden w-10 shrink-0 sm:block" />
          <div className="flex min-w-0 basis-full items-baseline gap-3 sm:block sm:flex-1 sm:basis-0">
            <label htmlFor="chapter-picker" className="sr-only">
              Chapter
            </label>
            <select
              id="chapter-picker"
              value={chapter?.section_id ?? ""}
              onChange={(e) => {
                const next = ready.find((c) => c.section_id === Number(e.target.value));
                if (next) void player.load(next, 0, playing);
              }}
              className="min-w-0 flex-1 cursor-pointer truncate rounded-lg bg-transparent text-sm text-ink sm:w-full"
            >
              {ready.map((c) => (
                <option key={c.section_id} value={c.section_id}>
                  {c.title ?? "Opening"}
                </option>
              ))}
            </select>
            <Chip>
              {formatClock(time)} / {formatClock(duration)}
            </Chip>
          </div>

          <div className="flex items-center">
            <button type="button" aria-label="Previous sentence" onClick={() => void player.step(-1)} className={ICON_BUTTON}>
              <Icon d={PREVIOUS} fill />
            </button>
            <button
              type="button"
              aria-label={playing ? "Pause" : "Play"}
              onClick={player.toggle}
              className="flex h-12 w-12 cursor-pointer items-center justify-center rounded-full bg-tungsten text-on-tungsten transition-transform duration-300 ease-spring active:scale-95"
            >
              <Icon d={playing ? PAUSE : PLAY} fill />
            </button>
            <button type="button" aria-label="Next sentence" onClick={() => void player.step(1)} className={ICON_BUTTON}>
              <Icon d={NEXT} fill />
            </button>
          </div>

          <div className="ml-auto flex items-center sm:ml-0">
            <button type="button" aria-label="Ask about the text" onClick={onAsk} className={ICON_BUTTON}>
              <Icon d={ASK} />
            </button>
            <label htmlFor="speed-picker" className="sr-only">
              Speed
            </label>
            <select
              id="speed-picker"
              value={player.speed}
              onChange={(e) => player.changeSpeed(Number(e.target.value))}
              className="min-h-11 cursor-pointer rounded-full bg-transparent px-2 font-mono text-xs text-ink-muted hover:text-ink"
            >
              {SPEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}×
                </option>
              ))}
            </select>
            <button
              type="button"
              aria-label="Highlight words as they're spoken"
              aria-pressed={player.highlight}
              onClick={() => player.setHighlight(!player.highlight)}
              className={`${ICON_BUTTON} ${player.highlight ? "text-tungsten" : ""}`}
            >
              <Icon d={HIGHLIGHT} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

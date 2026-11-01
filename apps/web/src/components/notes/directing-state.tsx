"use client";

import { useEffect, useState } from "react";
import { Bezel } from "@/components/bezel";
import { Orb } from "@/components/orb";
import type { DirectingProgress } from "@/lib/api";

function clock(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function batches(count: number) {
  return count === 1 ? "1 batch" : `${count} batches`;
}

type Step = { label: string; state: "done" | "active" | "waiting"; detail?: string };

/** The director's real stages, as the API reports them. Nothing here is a guess. */
function steps(progress: DirectingProgress | null, sentences: number): Step[] {
  const reading = !progress || progress.stage === "reading";
  let detail: string | undefined;
  if (progress?.stage === "labelling") {
    detail = `${progress.done} of ${batches(progress.total)} done · ${sentences.toLocaleString()} lines in all`;
  } else if (progress?.stage === "retrying") {
    detail = `Giving ${batches(progress.total - progress.done)} another try`;
  }
  return [
    { label: "Reading the whole text: genre, story and characters", state: reading ? "active" : "done" },
    { label: "Deciding how each line should sound", state: reading ? "waiting" : "active", detail },
    { label: "Casting a voice for every role", state: "waiting" },
  ];
}

export function DirectingState({ progress, sentences }: { progress: DirectingProgress | null; sentences: number }) {
  // Counted from when the director started (from the API), so a reload doesn't reset it
  const [now, setNow] = useState(() => Date.now());
  const [opened] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const elapsed = Math.max(0, Math.round(now / 1000 - (progress?.started_at ?? opened)));

  // A bar only once there's something real to measure: batches of lines labelled
  const fraction = progress && progress.stage !== "reading" && progress.total ? progress.done / progress.total : null;

  return (
    <Bezel>
      <div role="status" className="grid gap-10 p-8 md:grid-cols-[14rem_1fr] md:items-center md:p-12">
        <Orb level={elapsed % 2 ? 0.5 : 0.15} className="mx-auto w-40 md:w-full" />
        <div>
          <h2 className="font-display text-3xl tracking-tight md:text-4xl">The director is reading.</h2>
          <ol className="mt-6 flex flex-col gap-3">
            {steps(progress, sentences).map((step) => (
              <li key={step.label} className="flex items-baseline gap-3">
                <span
                  aria-hidden
                  className={`h-1.5 w-1.5 shrink-0 translate-y-[-2px] rounded-full ${
                    step.state === "active" ? "animate-pulse bg-tungsten" : step.state === "done" ? "bg-tungsten/70" : "bg-ink-faint"
                  }`}
                />
                <span className={step.state === "waiting" ? "text-ink-faint" : step.state === "done" ? "text-ink-muted" : "text-ink"}>
                  {step.label}
                  {step.state === "done" && <span className="sr-only"> (done)</span>}
                  {step.detail && <span className="mt-1 block font-mono text-xs text-ink-muted">{step.detail}</span>}
                </span>
              </li>
            ))}
          </ol>
          {fraction !== null && (
            <div
              role="progressbar"
              aria-label="Lines directed"
              aria-valuenow={Math.round(fraction * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              className="mt-6 h-1 overflow-hidden rounded-full bg-ink/[0.08]"
            >
              <div
                className="h-full rounded-full bg-tungsten transition-[width] duration-700 ease-spring"
                style={{ width: `${Math.max(4, fraction * 100)}%` }}
              />
            </div>
          )}
          <p className="mt-6 font-mono text-xs text-ink-muted">{clock(elapsed)} so far</p>
        </div>
      </div>
    </Bezel>
  );
}

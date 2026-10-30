"use client";

import { useEffect, useState } from "react";
import { Bezel } from "@/components/bezel";
import { Orb } from "@/components/orb";
import { estimateDirectingSeconds } from "@/lib/vocabulary";

const STEPS = [
  "Reading the whole text for its genre and characters",
  "Casting a voice for every role",
  "Deciding how each line should sound",
];

function clock(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

// No fake progress bar: the API doesn't report progress yet, so we say what's
// happening, how long it's been, and an honest estimate from the document's size.
export function DirectingState({ sentences }: { sentences: number }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const estimate = estimateDirectingSeconds(sentences);

  return (
    <Bezel>
      <div role="status" className="grid gap-10 p-8 md:grid-cols-[14rem_1fr] md:items-center md:p-12">
        <Orb level={elapsed % 2 ? 0.5 : 0.15} className="mx-auto w-40 md:w-full" />
        <div>
          <h2 className="font-display text-3xl tracking-tight md:text-4xl">The director is reading.</h2>
          <ul className="mt-6 flex flex-col gap-3 text-ink-muted">
            {STEPS.map((step) => (
              <li key={step} className="flex items-baseline gap-3">
                <span aria-hidden className="h-1.5 w-1.5 shrink-0 translate-y-[-2px] rounded-full bg-tungsten/70" />
                {step}
              </li>
            ))}
          </ul>
          <p className="mt-8 font-mono text-xs text-ink-muted">
            {clock(elapsed)} so far · usually about {clock(estimate)} for {sentences.toLocaleString()} lines
          </p>
        </div>
      </div>
    </Bezel>
  );
}

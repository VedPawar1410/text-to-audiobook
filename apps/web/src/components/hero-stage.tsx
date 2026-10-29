"use client";

import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { Bezel } from "./bezel";
import { Orb } from "./orb";

// An original line, performed word by word to preview the read-along reader.
const LINE =
  "Every timeline ends. The only question is who will be standing there when it does.";
const WORDS = LINE.split(" ");

const WORD_MS = 330;
const SENTENCE_PAUSE_MS = 900;
const LOOP_PAUSE_MS = 2200;

// Orb + read-along demo share one clock, so the voice visibly "speaks" each word.
export function HeroStage() {
  const reduce = useReducedMotion();
  const [index, setIndex] = useState(reduce ? 1 : 0);

  useEffect(() => {
    if (reduce) return;
    const word = WORDS[index];
    const isLast = index === WORDS.length - 1;
    const delay = isLast ? LOOP_PAUSE_MS : word.endsWith(".") ? SENTENCE_PAUSE_MS : WORD_MS;
    const timer = setTimeout(() => setIndex(isLast ? 0 : index + 1), delay);
    return () => clearTimeout(timer);
  }, [index, reduce]);

  // Longer words "sound" louder; a crude stand-in for real audio levels.
  const level = reduce ? 0 : Math.min(1, 0.35 + WORDS[index].length * 0.07);

  return (
    <>
      <div className="flex justify-center md:col-span-5">
        <Orb level={level} className="w-64 md:w-full md:max-w-sm" />
      </div>

      <Bezel className="md:col-span-12">
        <div className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:gap-10 md:p-10">
          <span className="shrink-0 font-mono text-[11px] tracking-[0.2em] text-ink-muted uppercase">
            Read-along preview
          </span>
          <p className="font-read text-2xl leading-snug md:text-3xl">
            {WORDS.map((word, i) => (
              // `isolate` keeps the -z-10 glow behind this word, not behind the whole card
              <span key={i} className="relative isolate inline-block px-[0.12em]">
                {i === index && (
                  <motion.span
                    layoutId="spoken-word"
                    className="absolute inset-0 -z-10 rounded-md bg-tungsten/20 ring-1 ring-tungsten/40"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <span
                  className={`transition-colors duration-300 ${i <= index ? "text-ink" : "text-ink-faint"}`}
                >
                  {word}
                </span>
              </span>
            ))}
          </p>
        </div>
      </Bezel>
    </>
  );
}

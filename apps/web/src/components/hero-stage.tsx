"use client";

import { motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { type HighlightStyle, useHighlightStyle } from "@/lib/highlight-style";
import { Bezel } from "./bezel";
import { HighlightPicker } from "./highlight-picker";
import { Orb } from "./orb";

// An original line, performed word by word to preview the read-along reader.
const LINE =
  "Every timeline ends. The only question is who will be standing there when it does.";
const WORDS = LINE.split(" ");

const WORD_MS = 330;
const SENTENCE_PAUSE_MS = 900;
const LOOP_PAUSE_MS = 2200;

function wordColor(style: HighlightStyle, i: number, index: number) {
  if (style === "off") return "text-ink";
  if (style === "ink" && i === index) return "text-tungsten";
  return i <= index ? "text-ink" : "text-ink-faint";
}

// Orb + read-along demo share one clock, so the voice visibly "speaks" each word.
export function HeroStage() {
  const reduce = useReducedMotion();
  const [index, setIndex] = useState(reduce ? 1 : 0);
  const [style, setStyle] = useHighlightStyle();

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
        <div className="flex flex-col gap-4 p-6 md:flex-row md:items-start md:gap-10 md:p-10">
          <span className="shrink-0 font-mono text-[11px] tracking-[0.2em] text-ink-muted uppercase md:pt-3">
            Read-along preview
          </span>
          <div className="flex flex-col gap-8">
            <p className="font-read text-2xl leading-snug md:text-3xl">
              {WORDS.map((word, i) => (
                // `isolate` keeps the -z-10 marks behind this word, not behind the whole card
                <span key={i} className="relative isolate inline-block px-[0.12em]">
                  {i === index && style === "glow" && (
                    <motion.span
                      layoutId="spoken-word"
                      className="absolute inset-0 -z-10 rounded-md bg-tungsten/20 ring-1 ring-tungsten/40"
                      transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    />
                  )}
                  {i === index && style === "underline" && (
                    <motion.span
                      layoutId="spoken-underline"
                      className="absolute inset-x-[0.12em] bottom-[0.02em] -z-10 h-[2px] rounded-full bg-tungsten"
                      transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    />
                  )}
                  <span className={`transition-colors duration-300 ${wordColor(style, i, index)}`}>{word}</span>
                </span>
              ))}
            </p>
            <HighlightPicker name="hero-highlight" value={style} onChange={setStyle} showHint />
          </div>
        </div>
      </Bezel>
    </>
  );
}

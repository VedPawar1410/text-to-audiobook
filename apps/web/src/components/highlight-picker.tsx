"use client";

import { motion } from "motion/react";
import { HIGHLIGHT_STYLES, type HighlightStyle } from "@/lib/highlight-style";

type Props = {
  name: string; // unique per page, so two pickers don't share one radio group
  value: HighlightStyle;
  onChange: (style: HighlightStyle) => void;
  showHint?: boolean;
};

/** Segmented control. Native radios underneath, so arrow keys and screen readers just work. */
export function HighlightPicker({ name, value, onChange, showHint = false }: Props) {
  const hint = HIGHLIGHT_STYLES.find((s) => s.id === value)?.hint;
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="sr-only">Highlight style</legend>
      {/* A 2×2 grid on phones (four in a row doesn't fit), one row from sm up */}
      <div className="grid grid-cols-2 gap-1 rounded-3xl border border-hairline bg-stage p-1 sm:flex sm:w-fit sm:rounded-full">
        {HIGHLIGHT_STYLES.map((style) => {
          const checked = style.id === value;
          return (
            <label
              key={style.id}
              className={`relative isolate flex min-h-11 cursor-pointer items-center justify-center rounded-full px-4 text-sm transition-colors duration-300 ease-spring has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-tungsten ${
                checked ? "text-on-tungsten" : "text-ink-muted hover:text-ink"
              }`}
            >
              <input
                type="radio"
                name={name}
                value={style.id}
                checked={checked}
                onChange={() => onChange(style.id)}
                className="sr-only"
              />
              {checked && (
                <motion.span
                  layoutId={`${name}-thumb`}
                  aria-hidden
                  className="absolute inset-0 -z-10 rounded-full bg-tungsten"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                />
              )}
              {style.label}
            </label>
          );
        })}
      </div>
      {showHint && <p className="pl-1 text-sm text-ink-muted">{hint}</p>}
    </fieldset>
  );
}

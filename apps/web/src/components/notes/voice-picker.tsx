"use client";

import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import type { Voice } from "@/lib/api";

type Props = {
  voices: Voice[];
  value: string;
  labelledBy: string; // the visible label's id: the button itself reads out the chosen voice
  disabled?: boolean;
  describedBy?: string;
  onChange: (voiceId: string) => void;
};

function groupName(voice: Voice) {
  return `${voice.accent} · ${voice.gender}`;
}

/**
 * A custom select, built to the WAI-ARIA "select-only combobox" pattern: focus stays on
 * the button, aria-activedescendant points at the highlighted option. Arrows, Home/End,
 * Enter, Escape and type-to-jump all work, as they do in a native <select>.
 */
export function VoicePicker({ voices, value, labelledBy, disabled = false, describedBy, onChange }: Props) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLDivElement>(null);

  // Options are indexed in display order (grouped), so keyboard moves follow what's on screen
  const groups = Object.entries(Object.groupBy(voices, groupName) as Record<string, Voice[]>);
  const ordered = groups.flatMap(([, members]) => members);
  const current = voices.find((v) => v.id === value);
  const optionId = (index: number) => `${id}-option-${index}`;

  // Close on a click anywhere else
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    window.addEventListener("pointerdown", onPointer);
    return () => window.removeEventListener("pointerdown", onPointer);
  }, [open]);

  // Keep the highlighted option visible while moving with the keyboard
  useEffect(() => {
    if (!open) return;
    list.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  function show() {
    setActive(Math.max(0, ordered.findIndex((v) => v.id === value)));
    setOpen(true);
  }

  function choose(index: number) {
    setOpen(false);
    const voice = ordered[index];
    if (voice && voice.id !== value) onChange(voice.id);
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const last = ordered.length - 1;
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
        event.preventDefault();
        show();
      }
      return;
    }
    const moves: Record<string, number> = {
      ArrowDown: Math.min(last, active + 1),
      ArrowUp: Math.max(0, active - 1),
      Home: 0,
      End: last,
      PageDown: Math.min(last, active + 8),
      PageUp: Math.max(0, active - 8),
    };
    if (event.key in moves) {
      event.preventDefault();
      setActive(moves[event.key]);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      choose(active);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
    } else if (event.key === "Tab") {
      setOpen(false);
    } else if (/^[a-z]$/i.test(event.key)) {
      // Type a letter to jump to the next voice starting with it
      const letter = event.key.toLowerCase();
      const after = [...ordered.keys()].map((i) => (active + 1 + i) % ordered.length);
      const match = after.find((i) => ordered[i].name.toLowerCase().startsWith(letter));
      if (match !== undefined) setActive(match);
    }
  }

  let index = -1; // running option index across the groups
  return (
    <div ref={root} className="relative">
      <button
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-activedescendant={open ? optionId(active) : undefined}
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        disabled={disabled || voices.length === 0}
        onClick={() => (open ? setOpen(false) : show())}
        onKeyDown={onKeyDown}
        className="flex min-h-12 w-full cursor-pointer items-center justify-between gap-3 rounded-2xl border border-hairline bg-stage px-4 py-2 text-left transition-colors duration-300 ease-spring hover:border-ink/20 disabled:cursor-wait disabled:opacity-50"
      >
        <span className="min-w-0">
          <span className="block truncate text-sm text-ink">{current?.name ?? value}</span>
          {current && <span className="block truncate text-xs text-ink-muted capitalize">{groupName(current)}</span>}
        </span>
        <svg
          aria-hidden
          viewBox="0 0 16 16"
          className={`h-4 w-4 shrink-0 text-ink-muted transition-transform duration-300 ease-spring ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.25"
        >
          <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div
          ref={list}
          id={`${id}-list`}
          role="listbox"
          aria-label="Voices"
          className="absolute inset-x-0 top-full z-20 mt-2 max-h-72 overflow-y-auto overscroll-contain rounded-2xl border border-hairline bg-stage/95 p-1.5 shadow-[0_24px_48px_-12px_rgb(0_0_0/0.6)] backdrop-blur-xl"
        >
          {groups.map(([name, members], g) => (
            <div key={name} role="group" aria-labelledby={`${id}-group-${g}`}>
              <div
                id={`${id}-group-${g}`}
                role="presentation"
                className="sticky top-0 z-10 bg-stage px-3 pt-3 pb-1.5 font-mono text-[10px] tracking-[0.2em] text-ink-muted uppercase"
              >
                {name}
              </div>
              {members.map((voice) => {
                index += 1;
                const i = index;
                const selected = voice.id === value;
                return (
                  <div
                    key={voice.id}
                    id={optionId(i)}
                    data-index={i}
                    role="option"
                    aria-selected={selected}
                    onPointerMove={() => setActive(i)}
                    onClick={() => choose(i)}
                    className={`flex min-h-11 cursor-pointer items-center justify-between rounded-xl px-3 text-sm transition-colors duration-150 ${
                      i === active ? "bg-ink/[0.06]" : ""
                    } ${selected ? "text-tungsten" : i === active ? "text-ink" : "text-ink-muted"}`}
                  >
                    {voice.name}
                    {selected && (
                      <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M3.5 8.5 6.5 11.5 12.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import { useCallback, useSyncExternalStore } from "react";

/** How the read-along marks the spoken word. Picked on the homepage, used by the reader. */
export const HIGHLIGHT_STYLES = [
  { id: "glow", label: "Glow", hint: "A soft light follows the voice" },
  { id: "underline", label: "Underline", hint: "A line glides under each word" },
  { id: "ink", label: "Ink", hint: "Only the spoken word changes colour" },
  { id: "off", label: "Off", hint: "Still text, nothing moves" },
] as const;

export type HighlightStyle = (typeof HIGHLIGHT_STYLES)[number]["id"];

const KEY = "narrate:highlight-style";
const DEFAULT: HighlightStyle = "glow";
const listeners = new Set<() => void>();
let unsaved: HighlightStyle = DEFAULT; // used when storage is blocked (private mode)

function isStyle(value: unknown): value is HighlightStyle {
  return HIGHLIGHT_STYLES.some((s) => s.id === value);
}

function read(): HighlightStyle {
  try {
    const saved = window.localStorage.getItem(KEY);
    return isStyle(saved) ? saved : unsaved;
  } catch {
    return unsaved;
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  // Another tab changing the style updates this one too
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

/** The reader's chosen style, shared by every component on the page and remembered across visits. */
export function useHighlightStyle(): [HighlightStyle, (style: HighlightStyle) => void] {
  // useSyncExternalStore: the server (and first paint) use the default, then the saved choice
  const style = useSyncExternalStore(subscribe, read, () => DEFAULT);
  const setStyle = useCallback((next: HighlightStyle) => {
    unsaved = next;
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      // not remembered across visits, but still applied on this page
    }
    listeners.forEach((listener) => listener());
  }, []);
  return [style, setStyle];
}

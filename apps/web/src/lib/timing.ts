// Pure timing logic for read-along: no DOM, no React. Tested with `npm test` (node --test).

export type ManifestWord = { text: string; start: number; end: number };
export type ManifestSegment = { segment_id: number; start: number; end: number; words: ManifestWord[] };
export type Manifest = { duration: number; segments: ManifestSegment[] };

/**
 * One line on a chapter's timeline. `words` is null when the spoken words don't match
 * the displayed ones (e.g. "INT." is said "Interior"); then the whole line is highlighted.
 */
export type Cue = { segmentId: number; start: number; end: number; words: ManifestWord[] | null };

export function displayWords(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}

/** Index of the last item starting at or before `time`, or -1. O(log n): cheap enough for every frame. */
export function lastStartingAt<T extends { start: number }>(items: readonly T[], time: number): number {
  let low = 0;
  let high = items.length - 1;
  let found = -1;
  while (low <= high) {
    const middle = (low + high) >> 1;
    if (items[middle].start <= time) {
      found = middle;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return found;
}

export function buildCues(manifest: Manifest, textOf: (segmentId: number) => string | undefined): Cue[] {
  return manifest.segments.map((segment) => {
    const shown = displayWords(textOf(segment.segment_id) ?? "");
    const aligned = segment.words.length > 0 && segment.words.length === shown.length;
    return { segmentId: segment.segment_id, start: segment.start, end: segment.end, words: aligned ? segment.words : null };
  });
}

/**
 * Where the voice is at `time`: the current line, and the word within it (-1 for whole-line cues).
 * Between lines and words it holds the last one, so the highlight never flickers through pauses.
 */
export function position(cues: readonly Cue[], time: number): { cue: number; word: number } {
  const cue = lastStartingAt(cues, time);
  if (cue < 0) return { cue: -1, word: -1 };
  const words = cues[cue].words;
  return { cue, word: words ? Math.max(0, lastStartingAt(words, time)) : -1 };
}

export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = String(total % 60).padStart(2, "0");
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${minutes}:${rest}`;
}

// Mirrors services/api/app/director/vocabulary.py (the API validates every edit,
// so a drift here shows up as a clear error rather than bad data).
export const EMOTIONS = [
  "neutral", "warm", "joyful", "playful", "tender", "melancholic", "grief", "anxious",
  "suspenseful", "ominous", "angry", "cold", "determined", "awe", "surprised",
  "sarcastic", "urgent", "weary", "whispering", "authoritative",
] as const;

const GENRE_LABELS: Record<string, string> = {
  scifi_action: "Sci-fi & action",
  childrens: "Children's",
  self_help: "Self-help",
  art: "Art & criticism",
};

export function genreLabel(genre: string | null): string {
  if (!genre) return "";
  return GENRE_LABELS[genre] ?? genre.charAt(0).toUpperCase() + genre.slice(1);
}

export function formatDuration(minutes: number): string {
  if (minutes < 1) return "under a minute";
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hours = Math.floor(minutes / 60);
  const rest = Math.round(minutes % 60);
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

/** Rough directing time: one whole-document call, then chunks of 150 lines, 3 at a time. */
export function estimateDirectingSeconds(sentences: number): number {
  return 25 + Math.ceil(sentences / 450) * 25;
}

export function titleCase(id: string): string {
  return id.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

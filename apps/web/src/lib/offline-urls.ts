/** Everything the reader fetches for one book, so saving these makes it playable offline. */
export type SavableChapter = { section_id: number; version: string | null; duration_s: number | null };

export function bookUrls(documentId: string, chapters: SavableChapter[]) {
  const base = `/api/documents/${documentId}`;
  return {
    data: [
      base,
      `${base}/render`,
      ...chapters.map((c) => `${base}/chapters/${c.section_id}/manifest?v=${c.version}`),
    ],
    audio: chapters.map((c) => `${base}/chapters/${c.section_id}/audio?v=${c.version}`),
  };
}

/** Chapters are MP3s at 64 kbps: 8,000 bytes per second. */
export function estimateBytes(chapters: SavableChapter[]): number {
  return Math.round(chapters.reduce((total, c) => total + (c.duration_s ?? 0), 0) * 8000);
}

export function formatSize(bytes: number): string {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.max(1, Math.round(bytes / 1e6))} MB`;
}

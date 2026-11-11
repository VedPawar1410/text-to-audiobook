import { bookUrls, type SavableChapter } from "./offline-urls";

/**
 * "Save for offline": a book's data, timings and audio go into Cache Storage, and the service
 * worker (public/sw.js) answers from there. The state is always checked against what is really
 * stored, so a book iOS cleared, or one re-recorded since, says so instead of failing silently.
 */
const CACHE = "narrate-books-v1";
const key = (id: string) => `narrate:offline:${id}`;

export type OfflineState = { kind: "none" } | { kind: "saved"; bytes: number } | { kind: "stale" };

export const offlineSupported = () => typeof window !== "undefined" && "caches" in window;

export async function offlineState(id: string, chapters: SavableChapter[]): Promise<OfflineState> {
  const record = localStorage.getItem(key(id));
  if (!record) return { kind: "none" };
  const cache = await caches.open(CACHE);
  const { data, audio } = bookUrls(id, chapters);
  const present = await Promise.all([...data, ...audio].map((url) => cache.match(url)));
  return present.every(Boolean) ? { kind: "saved", bytes: JSON.parse(record).bytes } : { kind: "stale" };
}

export async function removeBook(id: string): Promise<void> {
  const cache = await caches.open(CACHE);
  const entries = await cache.keys();
  await Promise.all(entries.filter((r) => new URL(r.url).pathname.startsWith(`/api/documents/${id}`)).map((r) => cache.delete(r)));
  localStorage.removeItem(key(id));
}

/** All or nothing: if any file fails, nothing is left half-saved. */
export async function saveBook(id: string, chapters: SavableChapter[], onProgress: (done: number, total: number) => void): Promise<number> {
  const cache = await caches.open(CACHE);
  const { data, audio } = bookUrls(id, chapters);
  const urls = [...data, ...audio];
  let bytes = 0;
  try {
    await removeBook(id);
    for (const [index, url] of urls.entries()) {
      onProgress(index, urls.length);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Couldn't download part of this book (${response.status}).`);
      bytes += (await response.clone().blob()).size;
      await cache.put(url, response);
    }
  } catch (error) {
    await removeBook(id);
    throw error;
  }
  localStorage.setItem(key(id), JSON.stringify({ bytes }));
  await navigator.storage?.persist?.().catch(() => false); // ask iOS to keep it; best effort
  return bytes;
}

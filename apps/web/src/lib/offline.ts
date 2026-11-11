import type { DocumentSummary } from "./api";
import { bookUrls, staticAssets, type SavableChapter } from "./offline-urls";

/**
 * "Save for offline": a book's data, timings and audio go into Cache Storage, along with the
 * pages and code the app needs to open without a connection, and the service worker
 * (public/sw.js) answers from there. The state is always checked against what is really
 * stored, so a book iOS cleared, or one re-recorded since, says so instead of failing silently.
 */
const CACHE = "narrate-books-v1";
const PREFIX = "narrate:offline:";
const key = (id: string) => `${PREFIX}${id}`;

export type OfflineState = { kind: "none" } | { kind: "saved"; bytes: number } | { kind: "stale" };

export const offlineSupported = () => typeof window !== "undefined" && "caches" in window;

export async function offlineState(id: string, chapters: SavableChapter[]): Promise<OfflineState> {
  const record = localStorage.getItem(key(id));
  if (!record) return { kind: "none" };
  const cache = await caches.open(CACHE);
  const { pages, data, audio } = bookUrls(id, chapters);
  const present = await Promise.all([...pages, ...data, ...audio].map((url) => cache.match(url)));
  return present.every(Boolean) ? { kind: "saved", bytes: JSON.parse(record).bytes } : { kind: "stale" };
}

export function savedBookIds(): string[] {
  if (!offlineSupported()) return [];
  return Object.keys(localStorage)
    .filter((k) => k.startsWith(PREFIX))
    .map((k) => k.slice(PREFIX.length));
}

/** The books that can really open offline, read straight from the phone, newest first. */
export async function savedBooks(): Promise<DocumentSummary[]> {
  if (!offlineSupported()) return [];
  const cache = await caches.open(CACHE);
  const found = await Promise.all(
    savedBookIds().map(async (id) => ((await cache.match(`/documents/${id}/listen`)) ? cache.match(`/api/documents/${id}`) : undefined)),
  );
  const books: DocumentSummary[] = await Promise.all(found.filter((r) => r !== undefined).map((r) => r.json()));
  return books.sort((a, b) => b.created_at.localeCompare(a.created_at));
}

/** Removes this book. The shared Library page and app code stay: other books may need them. */
export async function removeBook(id: string): Promise<void> {
  const cache = await caches.open(CACHE);
  const entries = await cache.keys();
  const mine = (r: Request) => [`/api/documents/${id}`, `/documents/${id}`].some((p) => new URL(r.url).pathname.startsWith(p));
  await Promise.all(entries.filter(mine).map((r) => cache.delete(r)));
  localStorage.removeItem(key(id));
}

/** All or nothing: if any file fails, nothing is left half-saved. */
export async function saveBook(id: string, chapters: SavableChapter[], onProgress: (done: number, total: number) => void): Promise<number> {
  const cache = await caches.open(CACHE);
  const { pages, data, audio } = bookUrls(id, chapters);
  const urls = [...data, ...audio];

  async function saveFile(url: string): Promise<Response> {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Couldn't download part of this book (${response.status}).`);
    await cache.put(url, response.clone());
    return response;
  }

  let bytes = 0;
  try {
    await removeBook(id);
    onProgress(0, urls.length);
    const htmls = await Promise.all(pages.map(async (page) => (await saveFile(page)).text()));
    await Promise.all(staticAssets(htmls.join("")).map(async (url) => (await cache.match(url)) ?? saveFile(url)));
    for (const [index, url] of urls.entries()) {
      onProgress(index, urls.length);
      bytes += (await (await saveFile(url)).blob()).size;
    }
  } catch (error) {
    await removeBook(id);
    throw error;
  }
  localStorage.setItem(key(id), JSON.stringify({ bytes }));
  await navigator.storage?.persist?.().catch(() => false); // ask iOS to keep it; best effort
  return bytes;
}

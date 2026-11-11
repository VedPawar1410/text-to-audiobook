"use client";

import { useEffect, useRef, useState } from "react";
import { PillButton } from "@/components/pill-link";
import { api, chapterAudioUrl } from "@/lib/api";

/**
 * P3.2 of the PWA plan: can a saved book play in airplane mode on a real iPhone? iPhones fetch
 * media in byte ranges, so a saved file has to answer those correctly. Tries both designs:
 * the file through the service worker (the reader's code stays the same) and from memory as a
 * blob URL (the fallback). Each test measures playback and seeking.
 */
type Source = { url: string; title: string };
type Result = { method: string; online: boolean; played: number; seekTarget: number; afterSeek: number; seekOk: boolean; error: string | null; swAudioRequests: number; swRanges: string[] };

const CACHE = "narrate-offline-test";
const KEY = "narrate-offline-source";
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function OfflineTest() {
  const audio = useRef<HTMLAudioElement | null>(null);
  const blobUrl = useRef<string | null>(null);
  const seen = useRef<string[]>([]);
  const requests = useRef(0);
  const [source, setSource] = useState<Source | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [status, setStatus] = useState("Registering the service worker…");
  const [controlled, setControlled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<Result[]>([]);
  const [copied, setCopied] = useState(false);

  async function prepareBlob(url: string) {
    const cached = await (await caches.open(CACHE)).match(url);
    if (!cached) return false;
    const blob = await cached.blob();
    if (blobUrl.current) URL.revokeObjectURL(blobUrl.current);
    blobUrl.current = URL.createObjectURL(blob);
    setSaved(`${(blob.size / 1e6).toFixed(1)} MB saved`);
    return true;
  }

  useEffect(() => {
    if (!("serviceWorker" in navigator)) {
      void Promise.resolve().then(() => setStatus("This browser has no service workers (they need HTTPS)."));
      return;
    }
    const onMessage = (event: MessageEvent) => {
      if (event.data?.kind !== "audio") return;
      requests.current += 1;
      if (event.data.range) seen.current.push(event.data.range);
    };
    navigator.serviceWorker.addEventListener("message", onMessage);
    (async () => {
      await navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" });
      await navigator.serviceWorker.ready;
      setControlled(Boolean(navigator.serviceWorker.controller));
      navigator.serviceWorker.addEventListener("controllerchange", () => setControlled(true));
      // Remembered from an earlier save, so this also works with no network
      let found: Source | null = null;
      try {
        found = JSON.parse(localStorage.getItem(KEY) ?? "null");
      } catch {
        // blocked storage: look it up instead
      }
      if (!found) {
        let longest = 0;
        for (const doc of await api.listDocuments()) {
          for (const chapter of (await api.renderStatus(doc.id)).chapters) {
            if (chapter.status === "ready" && (chapter.duration_s ?? 0) > longest) {
              longest = chapter.duration_s ?? 0;
              found = { url: chapterAudioUrl(doc.id, chapter), title: doc.title ?? "Untitled" };
            }
          }
        }
      }
      setSource(found);
      if (found) await prepareBlob(found.url);
      setStatus(found ? "Ready" : "No recorded book yet: record one first.");
    })().catch((e: Error) => setStatus(e.message));
    return () => navigator.serviceWorker.removeEventListener("message", onMessage);
  }, []);

  async function save() {
    if (!source) return;
    setBusy(true);
    setStatus("Saving…");
    try {
      const cache = await caches.open(CACHE);
      const response = await fetch(source.url);
      if (!response.ok) throw new Error(`Couldn't download the audio (${response.status}).`);
      await cache.put(source.url, response);
      localStorage.setItem(KEY, JSON.stringify(source));
      await prepareBlob(source.url);
      setStatus("Saved. Now turn on airplane mode, keep this page open, and run both tests.");
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  // Called straight from a tap: iOS only lets audio start from a user gesture
  async function run(method: "service worker" | "from memory") {
    const element = audio.current;
    const url = method === "service worker" ? source?.url : blobUrl.current;
    if (!element || !url) return;
    setBusy(true);
    seen.current = [];
    requests.current = 0;
    let error: string | null = null;
    element.src = url;
    const started = element.play().catch((e: Error) => {
      error = e.message;
    });
    await started;
    await wait(4000);
    const played = element.currentTime;
    const seekTarget = Math.floor((element.duration || 60) / 2);
    element.currentTime = seekTarget;
    await wait(3000);
    const afterSeek = element.currentTime;
    element.pause();
    if (element.error) error = `media error ${element.error.code}`;
    setResults((all) => [
      ...all,
      {
        method,
        online: navigator.onLine,
        played: Math.round(played * 10) / 10,
        seekTarget,
        afterSeek: Math.round(afterSeek * 10) / 10,
        seekOk: afterSeek >= seekTarget && afterSeek < seekTarget + 10,
        error,
        swAudioRequests: requests.current,
        swRanges: seen.current.slice(0, 6),
      },
    ]);
    setBusy(false);
  }

  async function copy() {
    await navigator.clipboard.writeText(JSON.stringify({ controlled, saved, results }, null, 2));
    setCopied(true);
  }

  return (
    <div className="flex flex-col gap-8">
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
        <dt className="text-ink-muted">Status</dt>
        <dd>{status}</dd>
        <dt className="text-ink-muted">Service worker active</dt>
        <dd>{controlled ? "yes" : "not yet: reload this page once"}</dd>
        <dt className="text-ink-muted">Book</dt>
        <dd>{source?.title ?? "…"}</dd>
        <dt className="text-ink-muted">Saved</dt>
        <dd>{saved ?? "not yet"}</dd>
      </dl>

      <ol className="flex list-decimal flex-col gap-2 pl-5 text-ink-muted">
        <li>Tap Save. Wait until it shows the size.</li>
        <li>Turn on airplane mode (and Wi-Fi off). Keep this page open.</li>
        <li>Tap each test. Each takes about 7 seconds; you should hear audio, then a jump.</li>
        <li>Tap Copy results, turn airplane mode off, and send them over.</li>
      </ol>

      <div className="flex flex-wrap gap-3">
        <PillButton onClick={() => void save()} disabled={!source || busy}>
          Save
        </PillButton>
        <button type="button" onClick={() => void run("service worker")} disabled={!saved || busy} className="min-h-11 cursor-pointer rounded-full border border-hairline px-5 text-sm disabled:opacity-40">
          Test 1: saved file
        </button>
        <button type="button" onClick={() => void run("from memory")} disabled={!saved || busy} className="min-h-11 cursor-pointer rounded-full border border-hairline px-5 text-sm disabled:opacity-40">
          Test 2: from memory
        </button>
      </div>
      <audio ref={audio} preload="none" />

      <section aria-labelledby="offline-results" className="flex flex-col gap-3">
        <h2 id="offline-results" className="font-display text-2xl tracking-tight">
          Results
        </h2>
        {results.length === 0 ? (
          <p className="text-sm text-ink-muted">None yet.</p>
        ) : (
          <ul className="flex flex-col gap-2 text-sm">
            {results.map((r, index) => (
              <li key={index} className="rounded-2xl border border-hairline px-4 py-3">
                <span className="font-medium">{r.method}</span> ({r.online ? "online" : "offline"}): played to {r.played} s, seek to {r.seekTarget} s landed at {r.afterSeek} s
                {r.seekOk ? " ✓" : " ✗"} · service worker saw {r.swAudioRequests} audio requests{r.error ? ` · ${r.error}` : ""}
              </li>
            ))}
          </ul>
        )}
        <button type="button" onClick={() => void copy()} disabled={!results.length} className="min-h-11 w-max cursor-pointer rounded-full border border-hairline px-5 text-sm disabled:opacity-40">
          {copied ? "Copied" : "Copy results"}
        </button>
      </section>
    </div>
  );
}

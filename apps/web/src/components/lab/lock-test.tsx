"use client";

import { useEffect, useRef, useState } from "react";
import { PillButton } from "@/components/pill-link";
import { api, chapterAudioUrl } from "@/lib/api";

/**
 * P2 of the PWA plan: measure, on a real iPhone, whether audio keeps playing when the phone is
 * locked, in a Safari tab vs. as a home-screen web app. Reports suggest iOS pauses installed web
 * apps on lock; this page turns that into numbers: seconds locked vs. seconds of audio played.
 * Results are kept in this browser (localStorage) and can be copied as JSON.
 */
type Run = { mode: string; lockedSeconds: number; playedSeconds: number; stillPlaying: boolean; controls: string[]; at: string };

const KEY = "narrate-lock-test";

function displayMode(): string {
  const iosStandalone = (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return window.matchMedia("(display-mode: standalone)").matches || iosStandalone ? "installed web app" : "Safari tab";
}

export function LockTest() {
  const audio = useRef<HTMLAudioElement | null>(null);
  const hidden = useRef<{ wall: number; audio: number; controls: string[] } | null>(null);
  const [source, setSource] = useState<{ url: string; title: string } | null>(null);
  const [status, setStatus] = useState("Finding a recorded book…");
  const [playing, setPlaying] = useState(false);
  const [info, setInfo] = useState<[string, string][]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [copied, setCopied] = useState(false);

  // The first chapter that's already recorded
  useEffect(() => {
    (async () => {
      for (const doc of await api.listDocuments()) {
        const chapter = (await api.renderStatus(doc.id)).chapters.find((c) => c.status === "ready");
        if (chapter) {
          setSource({ url: chapterAudioUrl(doc.id, chapter), title: doc.title ?? "Untitled" });
          setStatus("Ready");
          return;
        }
      }
      setStatus("No recorded book yet: record one first.");
    })().catch((e: Error) => setStatus(e.message));
  }, []);

  // What iOS gives this page: display mode, storage quota, persistence
  useEffect(() => {
    (async () => {
      const estimate = navigator.storage?.estimate ? await navigator.storage.estimate() : null;
      const persisted = navigator.storage?.persisted ? await navigator.storage.persisted() : null;
      setInfo([
        ["Running as", displayMode()],
        ["Storage quota", estimate?.quota ? `${(estimate.quota / 1e9).toFixed(1)} GB` : "unknown"],
        ["Storage used", estimate?.usage != null ? `${(estimate.usage / 1e6).toFixed(1)} MB` : "unknown"],
        ["Storage persisted", String(persisted)],
        ["Lock-screen API", "mediaSession" in navigator ? "yes" : "no"],
        ["Browser", navigator.userAgent.replace(/^Mozilla\/5\.0 /, "")],
      ]);
      try {
        setRuns(JSON.parse(localStorage.getItem(KEY) ?? "[]"));
      } catch {
        // private browsing or blocked storage: results just aren't remembered
      }
    })();
  }, []);

  // Lock = the page becomes hidden. On return, compare wall-clock time with audio time.
  useEffect(() => {
    const onVisibility = () => {
      const element = audio.current;
      if (!element) return;
      if (document.visibilityState === "hidden") {
        if (!element.paused) hidden.current = { wall: Date.now(), audio: element.currentTime, controls: [] };
        return;
      }
      const start = hidden.current;
      hidden.current = null;
      if (!start) return;
      const run: Run = {
        mode: displayMode(),
        lockedSeconds: Math.round((Date.now() - start.wall) / 1000),
        playedSeconds: Math.max(0, Math.round(element.currentTime - start.audio)),
        stillPlaying: !element.paused,
        controls: start.controls,
        at: new Date().toISOString(),
      };
      setRuns((previous) => {
        const next = [...previous, run];
        try {
          localStorage.setItem(KEY, JSON.stringify(next));
        } catch {
          // as above
        }
        return next;
      });
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  function toggle() {
    const element = audio.current;
    if (!element || !source) return;
    if (!element.paused) {
      element.pause();
      return;
    }
    if ("mediaSession" in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({ title: "Lock test", artist: source.title, album: "Narrate" });
      // Record taps on the lock-screen controls while locked
      const note = (name: string, action: () => void) => () => {
        hidden.current?.controls.push(name);
        action();
      };
      navigator.mediaSession.setActionHandler("play", note("play", () => void element.play()));
      navigator.mediaSession.setActionHandler("pause", note("pause", () => element.pause()));
    }
    void element.play();
  }

  async function copy() {
    const report = { info: Object.fromEntries(info), runs };
    await navigator.clipboard.writeText(JSON.stringify(report, null, 2));
    setCopied(true);
  }

  function clear() {
    setRuns([]);
    try {
      localStorage.removeItem(KEY);
    } catch {
      // as above
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
        {info.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-ink-muted">{label}</dt>
            <dd className="font-mono text-xs leading-5 break-words">{value}</dd>
          </div>
        ))}
      </dl>

      <ol className="flex list-decimal flex-col gap-2 pl-5 text-ink-muted">
        <li>Press Play below and let it play for a few seconds.</li>
        <li>Lock the phone. Wait about 30 seconds (try the lock-screen controls if they show).</li>
        <li>Unlock and come back to this page: a result appears below.</li>
        <li>Repeat after adding this page to your Home Screen, then copy the results.</li>
      </ol>

      <div className="flex flex-wrap items-center gap-4">
        <PillButton onClick={toggle} disabled={!source}>
          {playing ? "Pause" : "Play"}
        </PillButton>
        <p className="text-sm text-ink-muted">{source ? source.title : status}</p>
      </div>
      {source && (
        <audio ref={audio} src={source.url} preload="auto" onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} />
      )}

      <section aria-labelledby="results-heading" className="flex flex-col gap-3">
        <h2 id="results-heading" className="font-display text-2xl tracking-tight">
          Results
        </h2>
        {runs.length === 0 ? (
          <p className="text-sm text-ink-muted">None yet.</p>
        ) : (
          <ul className="flex flex-col gap-2 text-sm">
            {runs.map((run) => (
              <li key={run.at} className="rounded-2xl border border-hairline px-4 py-3">
                <span className="font-medium">{run.mode}:</span> locked {run.lockedSeconds} s, audio played {run.playedSeconds} s
                {run.stillPlaying ? ", still playing" : ", stopped"}
                {run.controls.length > 0 && ` · lock-screen taps: ${run.controls.join(", ")}`}
              </li>
            ))}
          </ul>
        )}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => void copy()}
            disabled={!runs.length}
            className="min-h-11 cursor-pointer rounded-full border border-hairline px-5 text-sm hover:text-ink disabled:opacity-40"
          >
            {copied ? "Copied" : "Copy results"}
          </button>
          <button
            type="button"
            onClick={clear}
            disabled={!runs.length}
            className="min-h-11 cursor-pointer rounded-full px-5 text-sm text-ink-muted hover:text-ink disabled:opacity-40"
          >
            Clear
          </button>
        </div>
      </section>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { chapterAudioUrl, type Chapter, type DocumentDetail } from "./api";
import { buildCues, position, type Cue, type Manifest } from "./timing";

export const SPEEDS = [0.75, 1, 1.25, 1.5, 1.75, 2];
const SPEED_KEY = "narrate:speed";

// localStorage is a per-reader convenience (resume point, speed): never essential
function read<T>(key: string): T | null {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // private mode or storage blocked: playback still works
  }
}

function whenLoaded(audio: HTMLAudioElement) {
  return new Promise<void>((resolve) => {
    audio.addEventListener("loadedmetadata", () => resolve(), { once: true });
    audio.addEventListener("error", () => resolve(), { once: true });
  });
}

function keepInView(element: HTMLElement) {
  const { top, bottom } = element.getBoundingClientRect();
  // The player bar covers the bottom of the screen, so "comfortable" is the upper-middle band
  if (top < window.innerHeight * 0.18 || bottom > window.innerHeight * 0.62) {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    element.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
  }
}

type Saved = { sectionId: number; time: number };

/**
 * The read-along player: one <audio> element, chapter manifests, and the highlight.
 *
 * The highlight is painted by toggling two CSS classes straight on the DOM inside a
 * requestAnimationFrame loop. Doing it with React state would re-render every word
 * span (tens of thousands in a book) several times a second.
 */
export function useReadAlong(doc: DocumentDetail, chapters: Chapter[]) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const chapterRef = useRef<Chapter | null>(null);
  const cuesRef = useRef<Cue[]>([]);
  const manifests = useRef(new Map<string, Promise<Cue[]>>());
  const painted = useRef<{ line: HTMLElement | null; word: HTMLElement | null }>({ line: null, word: null });
  const highlightRef = useRef(true);
  const followRef = useRef(true);
  const lastSave = useRef(0);
  const positionKey = `narrate:position:${doc.id}`;

  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [highlight, setHighlightState] = useState(true);
  const [following, setFollowing] = useState(true);
  const [level, setLevel] = useState(0);
  const [resumed, setResumed] = useState(false);

  const ready = useMemo(() => chapters.filter((c) => c.status === "ready"), [chapters]);
  const textOf = useMemo(
    () => new Map(doc.sections.flatMap((s) => s.segments.map((g) => [g.id, g.text] as const))),
    [doc],
  );
  const sectionOf = useMemo(
    () => new Map(doc.sections.flatMap((s) => s.segments.map((g) => [g.id, s.id] as const))),
    [doc],
  );

  const cuesFor = useCallback(
    (target: Chapter) => {
      const key = `${target.section_id}:${target.version}`;
      let cues = manifests.current.get(key);
      if (!cues) {
        cues = fetch(`/api/documents/${doc.id}/chapters/${target.section_id}/manifest?v=${target.version}`)
          .then((response) => {
            if (!response.ok) throw new Error("Couldn't load the chapter's timings.");
            return response.json() as Promise<Manifest>;
          })
          .then((manifest) => buildCues(manifest, (id) => textOf.get(id)));
        cues.catch(() => manifests.current.delete(key)); // let a later attempt retry
        manifests.current.set(key, cues);
      }
      return cues;
    },
    [doc.id, textOf],
  );

  const paint = useCallback((cue: Cue | undefined, wordIndex: number) => {
    const on = highlightRef.current && cue;
    const line = on ? window.document.getElementById(`seg-${cue.segmentId}`) : null;
    const word = on && wordIndex >= 0 ? window.document.getElementById(`w-${cue.segmentId}-${wordIndex}`) : null;
    const previous = painted.current;

    if (previous.line !== line) {
      previous.line?.classList.remove("is-current-line");
      line?.classList.add("is-current-line");
      if (line && followRef.current) keepInView(line);
    }
    if (previous.word !== word) {
      previous.word?.classList.remove("is-current-word");
      word?.classList.add("is-current-word");
      if (word) setLevel(Math.min(1, 0.35 + (word.textContent?.length ?? 0) * 0.07)); // the orb pulses per word
    }
    painted.current = { line, word };
  }, []);

  const sync = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const { cue, word } = position(cuesRef.current, audio.currentTime);
    paint(cuesRef.current[cue], word);
  }, [paint]);

  const savePosition = useCallback(() => {
    const audio = audioRef.current;
    if (audio && chapterRef.current) write(positionKey, { sectionId: chapterRef.current.section_id, time: audio.currentTime });
  }, [positionKey]);

  // Created once and kept for the hook's lifetime. Effects only attach listeners: in dev,
  // Strict Mode (and Fast Refresh) re-run effects, and an element created inside an effect
  // would be replaced by a fresh one with no source while the loaded chapter is remembered.
  const getAudio = useCallback(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.preload = "metadata";
    }
    return audioRef.current;
  }, []);

  const load = useCallback(
    async (target: Chapter, startAt = 0, autoplay = false) => {
      const audio = getAudio();
      chapterRef.current = target;
      setChapter(target);
      const cues = await cuesFor(target).catch(() => [] as Cue[]);
      if (chapterRef.current !== target) return; // another chapter was chosen meanwhile
      cuesRef.current = cues;

      const src = chapterAudioUrl(doc.id, target);
      if (audio.dataset.src !== src) {
        audio.dataset.src = src;
        audio.src = src;
        await whenLoaded(audio);
      }
      audio.currentTime = startAt;
      if (autoplay) await audio.play().catch(() => undefined);
      sync();
    },
    [cuesFor, doc.id, getAudio, sync],
  );

  // One audio element for the whole session (so iOS only needs unlocking once)
  useEffect(() => {
    const audio = getAudio();

    const onTime = () => {
      setTime(audio.currentTime);
      if (Date.now() - lastSave.current > 5000) {
        lastSave.current = Date.now();
        savePosition();
      }
    };
    const onMeta = () => setDuration(audio.duration);
    const onPlay = () => setPlaying(true);
    const onPause = () => {
      setPlaying(false);
      savePosition();
    };
    const onSeeked = () => {
      setTime(audio.currentTime);
      sync();
    };

    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("loadedmetadata", onMeta);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    audio.addEventListener("seeked", onSeeked);
    return () => {
      audio.pause();
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("loadedmetadata", onMeta);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
      audio.removeEventListener("seeked", onSeeked);
    };
  }, [getAudio, savePosition, sync]);

  // At the end of a chapter, carry on with the next one
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onEnded = () => {
      const index = ready.findIndex((c) => c.section_id === chapterRef.current?.section_id);
      const next = ready[index + 1];
      if (next) void load(next, 0, true);
    };
    audio.addEventListener("ended", onEnded);
    return () => audio.removeEventListener("ended", onEnded);
  }, [ready, load]);

  // Start where the reader left off, or at the first recorded chapter; restore their speed
  useEffect(() => {
    if (chapterRef.current || ready.length === 0) return;
    const savedSpeed = read<number>(SPEED_KEY);
    if (savedSpeed && audioRef.current) {
      audioRef.current.defaultPlaybackRate = audioRef.current.playbackRate = savedSpeed;
    }
    const saved = read<Saved>(positionKey);
    const savedChapter = saved ? ready.find((c) => c.section_id === saved.sectionId) : undefined;
    const resume = saved && savedChapter && saved.time > 3 ? { chapter: savedChapter, time: saved.time } : null;
    // State updates happen once loading finishes (in a callback), not in the effect body
    void load(resume?.chapter ?? ready[0], resume?.time ?? 0).then(() => {
      if (savedSpeed) setSpeed(savedSpeed);
      if (resume) setResumed(true);
    });
  }, [ready, load, positionKey]);

  // Repaint every frame while playing (frames pause in background tabs; audio doesn't)
  useEffect(() => {
    if (!playing) return;
    let frame = 0;
    const tick = () => {
      sync();
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, sync]);

  // Scrolling by hand means "let me read elsewhere": stop following until asked
  useEffect(() => {
    const stop = () => {
      if (!followRef.current) return;
      followRef.current = false;
      setFollowing(false);
    };
    window.addEventListener("wheel", stop, { passive: true });
    window.addEventListener("touchmove", stop, { passive: true });
    return () => {
      window.removeEventListener("wheel", stop);
      window.removeEventListener("touchmove", stop);
    };
  }, []);

  const follow = useCallback(() => {
    followRef.current = true;
    setFollowing(true);
    painted.current.line?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, []);

  const toggle = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !chapterRef.current) return;
    if (audio.paused) {
      followRef.current = true;
      setFollowing(true);
      void audio.play().catch(() => undefined);
    } else {
      audio.pause();
    }
  }, []);

  const seek = useCallback((seconds: number) => {
    if (audioRef.current) audioRef.current.currentTime = seconds;
  }, []);

  const step = useCallback(
    async (direction: 1 | -1) => {
      const audio = audioRef.current;
      const current = chapterRef.current;
      if (!audio || !current) return;
      const cues = cuesRef.current;
      const { cue } = position(cues, audio.currentTime);
      // "Previous" first restarts the current sentence, like a music player's back button
      let target = cue + direction;
      if (direction === -1 && cue >= 0 && audio.currentTime - cues[cue].start > 1) target = cue;
      if (target >= 0 && target < cues.length) {
        audio.currentTime = cues[target].start;
        return;
      }
      const neighbour = ready[ready.findIndex((c) => c.section_id === current.section_id) + direction];
      if (!neighbour) return;
      const startAt = direction === 1 ? 0 : ((await cuesFor(neighbour).catch(() => [])).at(-1)?.start ?? 0);
      await load(neighbour, startAt, !audio.paused);
    },
    [ready, load, cuesFor],
  );

  /** Jump to a word (or a whole line when wordIndex is -1) and play from there. */
  const seekTo = useCallback(
    async (segmentId: number, wordIndex: number) => {
      const target = ready.find((c) => c.section_id === sectionOf.get(segmentId));
      if (!target) return;
      const cue = (await cuesFor(target).catch(() => [] as Cue[])).find((c) => c.segmentId === segmentId);
      if (!cue) return;
      const startAt = (wordIndex >= 0 && cue.words?.[wordIndex]?.start) || cue.start;
      followRef.current = true;
      setFollowing(true);
      if (chapterRef.current?.section_id === target.section_id && audioRef.current) {
        audioRef.current.currentTime = startAt;
        void audioRef.current.play().catch(() => undefined);
      } else {
        await load(target, startAt, true);
      }
    },
    [ready, sectionOf, cuesFor, load],
  );

  const changeSpeed = useCallback((next: number) => {
    setSpeed(next);
    write(SPEED_KEY, next);
    // defaultPlaybackRate survives switching chapters; playbackRate alone resets
    if (audioRef.current) audioRef.current.defaultPlaybackRate = audioRef.current.playbackRate = next;
  }, []);

  const setHighlight = useCallback(
    (on: boolean) => {
      highlightRef.current = on;
      setHighlightState(on);
      if (on) sync();
      else paint(undefined, -1);
    },
    [paint, sync],
  );

  // Lock-screen and headphone controls on phones
  useEffect(() => {
    if (!chapter || !("mediaSession" in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: chapter.title ?? doc.title ?? "Untitled",
      artist: "Narrate",
      album: doc.title ?? "",
    });
    const handlers: [MediaSessionAction, MediaSessionActionHandler][] = [
      ["play", () => void audioRef.current?.play()],
      ["pause", () => audioRef.current?.pause()],
      ["previoustrack", () => void step(-1)],
      ["nexttrack", () => void step(1)],
    ];
    for (const [action, handler] of handlers) {
      try {
        navigator.mediaSession.setActionHandler(action, handler);
      } catch {
        // an action this browser doesn't support
      }
    }
    return () => {
      for (const [action] of handlers) {
        try {
          navigator.mediaSession.setActionHandler(action, null);
        } catch {
          // as above
        }
      }
    };
  }, [chapter, doc.title, step]);

  return {
    ready,
    chapter,
    playing,
    time,
    duration,
    speed,
    highlight,
    following,
    resumed,
    level: playing ? level : 0,
    toggle,
    seek,
    step,
    seekTo,
    load,
    follow,
    changeSpeed,
    setHighlight,
  };
}

export type ReadAlong = ReturnType<typeof useReadAlong>;

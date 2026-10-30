"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type DocumentDetail, type Voice } from "./api";

const POLL_MS = 2000;
// A 44-byte silent WAV, used to "unlock" audio inside the click (see useVoicePreview)
const SILENT_WAV = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=";

/** Load a document, and keep polling while the director is working on it. */
export function useDocument(id: string) {
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const load = () =>
      api
        .getDocument(id)
        .then((doc) => {
          if (cancelled) return;
          setDocument(doc);
          setError(null);
          if (doc.status === "directing") timer = setTimeout(load, POLL_MS);
        })
        .catch((e: Error) => !cancelled && setError(e.message));

    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { document, setDocument, error, reload };
}

export function useVoices() {
  const [voices, setVoices] = useState<Voice[]>([]);
  useEffect(() => {
    api.voices().then(setVoices).catch(() => setVoices([]));
  }, []);
  return voices;
}

/** One shared audio element: starting a preview stops whichever one was playing. */
export function useVoicePreview() {
  const audio = useRef<HTMLAudioElement | null>(null);
  const objectUrl = useRef<string | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  const stop = useCallback(() => {
    audio.current?.pause();
    setPlaying(null);
  }, []);

  const play = useCallback(
    async (key: string, text: string, voice: string, speed: number) => {
      stop();
      setLoading(key);
      audio.current ??= new Audio();
      // Safari only lets audio start inside the click itself, and synthesis takes a moment
      // (several seconds on a cold server). Playing silence now unlocks the element.
      audio.current.src = SILENT_WAV;
      audio.current.play().catch(() => undefined);
      try {
        const blob = await api.previewVoice(text, voice, speed);
        if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
        objectUrl.current = URL.createObjectURL(blob);
        audio.current.src = objectUrl.current;
        audio.current.onended = () => setPlaying(null);
        await audio.current.play();
        setPlaying(key);
      } finally {
        setLoading(null);
      }
    },
    [stop],
  );

  useEffect(
    () => () => {
      audio.current?.pause();
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    },
    [],
  );

  return { play, stop, playing, loading };
}

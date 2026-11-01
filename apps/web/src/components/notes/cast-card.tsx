"use client";

import { type CSSProperties, useEffect, useRef, useState } from "react";
import { Bezel } from "@/components/bezel";
import { LABEL } from "@/components/ui";
import { api, type DocumentDetail, type Persona, type Voice } from "@/lib/api";
import { useVoicePreview, useVoices } from "@/lib/hooks";
import { VoicePicker } from "./voice-picker";

// A voice's natural range: beyond this Kokoro starts to sound rushed or drawn out
const MIN_SPEED = 0.7;
const MAX_SPEED = 1.3;
const FALLBACK_SAMPLE = "Every story deserves a voice. This is how I'll sound.";

/** The first substantial line this role speaks, so previews sound like the actual part. */
function sampleLine(document: DocumentDetail, castId: string): string {
  const lines = document.sections.flatMap((s) => s.segments).filter((g) => g.role === castId && g.text);
  const line = lines.find((g) => g.text.length > 25) ?? lines[0];
  return line ? line.text.slice(0, 300) : FALLBACK_SAMPLE;
}

export function CastSection({ document, onChange }: { document: DocumentDetail; onChange: (p: Persona) => void }) {
  const voices = useVoices();
  const preview = useVoicePreview();

  return (
    <section aria-labelledby="cast-heading">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 id="cast-heading" className="font-display text-3xl tracking-tight md:text-4xl">
          The cast
        </h2>
        <p className="max-w-sm text-sm text-ink-muted">Play a voice to hear its first line. Re-cast anyone you like.</p>
      </div>
      <ul className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {document.personas.map((persona) => (
          <li key={persona.cast_id}>
            <CastCard
              documentId={document.id}
              persona={persona}
              voices={voices}
              sample={sampleLine(document, persona.cast_id)}
              preview={preview}
              onChange={onChange}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

type CastCardProps = {
  documentId: string;
  persona: Persona;
  voices: Voice[];
  sample: string;
  preview: ReturnType<typeof useVoicePreview>;
  onChange: (p: Persona) => void;
};

function CastCard({ documentId, persona, voices, sample, preview, onChange }: CastCardProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftSpeed, setDraftSpeed] = useState<number | null>(null); // shown until the server has it
  const saveTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const key = persona.cast_id;
  const isPlaying = preview.playing === key;
  const isLoading = preview.loading === key;
  const errorId = `cast-error-${key}`;

  async function update(patch: Partial<Pick<Persona, "voice" | "speed">>) {
    setSaving(true);
    setError(null);
    preview.stop();
    try {
      onChange(await api.updatePersona(documentId, persona.cast_id, patch));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => () => clearTimeout(saveTimer.current), []);

  // The slider saves once it settles (400 ms after the last move), not on every step.
  // The draft stays on screen until then, so quick key presses build on each other.
  function changeSpeed(next: number) {
    setDraftSpeed(next);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      if (next !== persona.speed) await update({ speed: next });
      setDraftSpeed((current) => (current === next ? null : current));
    }, 400);
  }

  function togglePreview() {
    if (isPlaying) return preview.stop();
    preview.play(key, sample, persona.voice, persona.speed).catch(() => setError("Couldn't play this voice."));
  }

  const speed = draftSpeed ?? persona.speed;
  const progress = ((speed - MIN_SPEED) / (MAX_SPEED - MIN_SPEED)) * 100;

  return (
    <Bezel className="h-full">
      <div className="flex h-full flex-col gap-5 p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className={LABEL}>{key === "NARRATOR" ? "Narrator" : "Character"}</p>
            <h3 className="mt-2 truncate font-display text-2xl tracking-tight">{persona.display_name}</h3>
          </div>
          <button
            type="button"
            onClick={togglePreview}
            aria-label={isPlaying ? `Stop ${persona.display_name}` : `Hear ${persona.display_name}`}
            className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full bg-tungsten text-on-tungsten transition-transform duration-300 ease-spring active:scale-95"
          >
            {isLoading ? (
              <span aria-hidden className="h-4 w-4 animate-spin rounded-full border border-on-tungsten/30 border-t-on-tungsten" />
            ) : (
              <svg aria-hidden viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor">
                {isPlaying ? <rect x="4" y="4" width="8" height="8" rx="1" /> : <path d="M5 3.5v9l7.5-4.5z" />}
              </svg>
            )}
          </button>
        </div>

        <p className="font-read leading-relaxed text-ink-muted italic">&ldquo;{persona.description}&rdquo;</p>

        <div className="mt-auto flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <span id={`voice-label-${key}`} className={LABEL}>
              Voice
            </span>
            <VoicePicker
              voices={voices}
              value={persona.voice}
              labelledBy={`voice-label-${key}`}
              disabled={saving}
              describedBy={error ? errorId : undefined}
              onChange={(voice) => void update({ voice })}
            />
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between">
              <label htmlFor={`speed-${key}`} className={LABEL}>
                Speed
              </label>
              <span className="font-mono text-xs text-ink">{speed.toFixed(2)}×</span>
            </div>
            <input
              id={`speed-${key}`}
              type="range"
              min={MIN_SPEED}
              max={MAX_SPEED}
              step={0.01}
              value={speed}
              aria-valuetext={`${speed.toFixed(2)} times`}
              onChange={(e) => changeSpeed(Number(e.target.value))}
              style={{ "--progress": `${progress}%` } as CSSProperties}
              className="scrubber h-6 w-full"
            />
            <div aria-hidden className="flex justify-between font-mono text-[10px] tracking-[0.15em] text-ink-muted uppercase">
              <span>Slower</span>
              <span>Faster</span>
            </div>
          </div>
        </div>
        {error && (
          <p id={errorId} role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
      </div>
    </Bezel>
  );
}

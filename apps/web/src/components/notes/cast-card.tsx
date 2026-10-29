"use client";

import { useState } from "react";
import { Bezel } from "@/components/bezel";
import { LABEL, SELECT } from "@/components/ui";
import { api, type DocumentDetail, type Persona, type Voice } from "@/lib/api";
import { useVoicePreview, useVoices } from "@/lib/hooks";

const SPEEDS = [0.8, 0.85, 0.9, 0.95, 1, 1.05, 1.1, 1.15, 1.2];
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

  function togglePreview() {
    if (isPlaying) return preview.stop();
    preview.play(key, sample, persona.voice, persona.speed).catch(() => setError("Couldn't play this voice."));
  }

  const groups = Object.entries(
    Object.groupBy(voices, (v) => `${v.accent} · ${v.gender}`) as Record<string, Voice[]>,
  );
  const speeds = [...new Set([...SPEEDS, persona.speed])].sort((a, b) => a - b);

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

        <div className="mt-auto grid grid-cols-[1fr_6.5rem] gap-3">
          <label className="flex flex-col gap-1.5">
            <span className={LABEL}>Voice</span>
            <select
              value={persona.voice}
              disabled={saving}
              onChange={(e) => update({ voice: e.target.value })}
              aria-describedby={error ? errorId : undefined}
              className={SELECT}
            >
              {groups.length === 0 && <option value={persona.voice}>{persona.voice}</option>}
              {groups.map(([group, members]) => (
                <optgroup key={group} label={group}>
                  {members.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className={LABEL}>Speed</span>
            <select
              value={persona.speed}
              disabled={saving}
              onChange={(e) => update({ speed: Number(e.target.value) })}
              className={SELECT}
            >
              {speeds.map((s) => (
                <option key={s} value={s}>
                  {s.toFixed(2)}×
                </option>
              ))}
            </select>
          </label>
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

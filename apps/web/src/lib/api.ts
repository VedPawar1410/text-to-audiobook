// Typed client for the FastAPI service. Every call goes through /api/*,
// which next.config.ts proxies to the API, so the browser sees one origin.

export type Stats = {
  characters: number;
  words: number;
  sentences: number;
  speakers: string[];
  estimated_minutes: number;
};

export type ParsedDocument = {
  title: string | null;
  format: "prose" | "screenplay";
  sections: {
    title: string | null;
    blocks: { kind: string; text: string; speaker: string | null; direction: string | null; sentences: string[] }[];
  }[];
  stats: Stats;
};

export type Status = "parsed" | "directing" | "directed" | "failed";

export type DocumentSummary = {
  id: string;
  title: string | null;
  format: "prose" | "screenplay";
  status: Status;
  error: string | null;
  warning: string | null;
  genre: string | null;
  created_at: string;
  stats: Stats;
};

export type Persona = {
  cast_id: string;
  display_name: string;
  gender: string;
  age: string;
  accent: string;
  description: string;
  voice: string;
  speed: number;
};

export type Segment = {
  id: number;
  position: number;
  block_index: number;
  block_kind: string;
  text: string;
  speaker: string | null;
  block_direction: string | null;
  role: string;
  emotion: string;
  intensity: number;
  pace: string;
  pause_before_ms: number;
  pause_after_ms: number;
  emphasis: string[];
};

export type Section = { id: number; position: number; title: string | null; segments: Segment[] };

export type DocumentDetail = DocumentSummary & {
  subgenre: string | null;
  summary: string | null;
  narrator_style: string | null;
  personas: Persona[];
  sections: Section[];
};

export type Voice = { id: string; name: string; gender: "female" | "male"; accent: "American" | "British" };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    let message = `Something went wrong (${response.status}).`;
    try {
      const body = await response.json();
      // FastAPI sends a string detail for our errors, a list for validation errors
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) message = body.detail[0].msg;
    } catch {
      // not JSON: keep the generic message
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { "content-type": "application/json" }, body: JSON.stringify(body) };
}

export const api = {
  ingestText: (text: string) => request<ParsedDocument>("/ingest/text", json("POST", { text })),
  ingestUrl: (url: string) => request<ParsedDocument>("/ingest/url", json("POST", { url })),
  ingestFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ParsedDocument>("/ingest/file", { method: "POST", body: form });
  },

  saveDocument: (parsed: ParsedDocument) => request<DocumentSummary>("/documents", json("POST", parsed)),
  listDocuments: () => request<DocumentSummary[]>("/documents"),
  getDocument: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  direct: (id: string) => request<DocumentSummary>(`/documents/${id}/direct`, { method: "POST" }),
  rename: (id: string, title: string) => request<DocumentSummary>(`/documents/${id}`, json("PATCH", { title })),
  remove: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),
  updatePersona: (id: string, castId: string, patch: Partial<Pick<Persona, "voice" | "speed">>) =>
    request<Persona>(`/documents/${id}/personas/${encodeURIComponent(castId)}`, json("PATCH", patch)),
  updateSegment: (id: string, segmentId: number, patch: Partial<Pick<Segment, "emotion" | "intensity" | "role">>) =>
    request<Segment>(`/documents/${id}/segments/${segmentId}`, json("PATCH", patch)),

  voices: () => request<Voice[]>("/tts/voices"),
  previewVoice: async (text: string, voice: string, speed: number) => {
    const response = await fetch("/api/tts/preview", json("POST", { text, voice, speed }));
    if (!response.ok) throw new ApiError("Couldn't play this voice.", response.status);
    return response.blob();
  },
};

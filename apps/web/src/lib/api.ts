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

export type RenderJob = {
  id: number;
  status: "queued" | "rendering" | "done" | "failed" | "cancelled";
  total_lines: number;
  done_lines: number;
  error: string | null;
};

export type Chapter = {
  section_id: number;
  position: number;
  title: string | null;
  status: "pending" | "rendering" | "ready";
  duration_s: number | null;
  stale: boolean;
  version: string | null;
};

export type RenderStatus = { job: RenderJob | null; chapters: Chapter[] };

export const isRendering = (job: RenderJob | null) => job?.status === "queued" || job?.status === "rendering";

/** The version query changes on every re-render, so the browser never plays stale audio. */
export const chapterAudioUrl = (documentId: string, chapter: Chapter) =>
  `/api/documents/${documentId}/chapters/${chapter.section_id}/audio?v=${chapter.version}`;

export type ExportFormat = "m4b" | "mp3";

export type ExportInfo = { filename: string; size_bytes: number };

/** Serves the packaged file as a download (Content-Disposition: attachment). */
export const exportUrl = (documentId: string, format: ExportFormat) => `/api/documents/${documentId}/exports/${format}`;

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

export type AskTurn = { role: "user" | "assistant"; text: string };

export type AskRequest = { question: string; selection: string | null; segment_id: number | null; history: AskTurn[] };

/** Yields the answer as it's written (the API streams plain text). */
export async function* askStream(documentId: string, body: AskRequest): AsyncGenerator<string> {
  const response = await fetch(`/api/documents/${documentId}/ask`, json("POST", body));
  if (!response.ok || !response.body) {
    let message = "Couldn't ask right now.";
    try {
      const error = await response.json();
      if (typeof error.detail === "string") message = error.detail;
    } catch {
      // not JSON: keep the generic message
    }
    throw new ApiError(message, response.status);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    yield decoder.decode(value, { stream: true });
  }
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

  renderStatus: (id: string) => request<RenderStatus>(`/documents/${id}/render`),
  startRender: (id: string) => request<RenderStatus>(`/documents/${id}/render`, { method: "POST" }),
  cancelRender: (id: string) => request<void>(`/documents/${id}/render/cancel`, { method: "POST" }),
  /** Builds the download (an M4B of a long book takes a while), so the UI can show progress. */
  prepareExport: (id: string, format: ExportFormat) =>
    request<ExportInfo>(`/documents/${id}/exports/${format}`, { method: "POST" }),

  voices: () => request<Voice[]>("/tts/voices"),
  previewVoice: async (text: string, voice: string, speed: number) => {
    const response = await fetch("/api/tts/preview", json("POST", { text, voice, speed }));
    if (!response.ok) throw new ApiError("Couldn't play this voice.", response.status);
    return response.blob();
  },
};

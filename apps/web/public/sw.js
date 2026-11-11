// Serves saved books (lib/offline.ts). Registered for the whole app by components/service-worker.tsx.
//
// Answers saved audio from the cache, including the byte-range requests iPhones make for media,
// and falls back to saved copies when the server can't be reached. Anything never saved passes
// straight through, so a phone with no saved books behaves exactly as if this weren't here.
const WAIT_MS = 4000; // a sleeping Mac can leave a request hanging for a minute, so don't wait for it
const RETRY_AFTER_MS = 30000; // once it hasn't answered, use saved copies for a while without asking
let unreachableUntil = 0;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

async function report(message) {
  for (const client of await self.clients.matchAll({ includeUncontrolled: true })) client.postMessage(message);
}

/** A cached full file, answered as the slice the media element asked for. */
async function audioResponse(request, cached) {
  const blob = await cached.blob();
  const type = cached.headers.get("content-type") || "audio/mpeg";
  const range = request.headers.get("range");
  const match = range && /bytes=(\d*)-(\d*)/.exec(range);
  if (!match) {
    report({ kind: "audio", range: null, status: 200 });
    return new Response(blob, { status: 200, headers: { "Content-Type": type, "Content-Length": String(blob.size), "Accept-Ranges": "bytes" } });
  }
  const start = match[1] === "" ? Math.max(0, blob.size - Number(match[2])) : Number(match[1]);
  const end = match[1] !== "" && match[2] !== "" ? Math.min(Number(match[2]), blob.size - 1) : blob.size - 1;
  report({ kind: "audio", range, status: 206 });
  return new Response(blob.slice(start, end + 1), {
    status: 206,
    headers: {
      "Content-Type": type,
      "Content-Range": `bytes ${start}-${end}/${blob.size}`,
      "Content-Length": String(end - start + 1),
      "Accept-Ranges": "bytes",
    },
  });
}

/** The network if it answers in time, otherwise the fallback. */
async function networkOr(request, fallback) {
  if (!fallback) return fetch(request);
  if (Date.now() < unreachableUntil) return fallback;
  try {
    const timeout = new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), WAIT_MS));
    return await Promise.race([fetch(request), timeout]);
  } catch {
    unreachableUntil = Date.now() + RETRY_AFTER_MS;
    return fallback;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  event.respondWith(
    (async () => {
      const cached = await caches.match(request.url); // across saved books and the lab test
      if (cached && url.pathname.endsWith("/audio")) return audioResponse(request, cached);
      if (cached && url.pathname.startsWith("/_next/static/")) return cached; // hashed names never change
      if (cached) return networkOr(request, cached);
      // A page that was never saved: with no connection, go to the Library instead of an error
      const library = new URL("/documents", url).href;
      const isPage = request.mode === "navigate" && !url.pathname.startsWith("/api/");
      return networkOr(request, isPage && (await caches.match(library)) ? Response.redirect(library, 302) : undefined);
    })(),
  );
});

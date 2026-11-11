// Offline audio test (P3.2 of the PWA plan). Registered only from /lab/offline-test.
//
// Two jobs: answer audio requests from the cache, including the byte-range requests iPhones
// make for media, and fall back to the cache when the network fails. Everything else passes
// straight through, so this can't change how the app behaves online.
const CACHE = "narrate-offline-test";

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

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  event.respondWith(
    (async () => {
      const cached = await (await caches.open(CACHE)).match(request.url);
      if (cached && url.pathname.endsWith("/audio")) return audioResponse(request, cached);
      try {
        return await fetch(request);
      } catch (error) {
        if (cached) return cached;
        throw error;
      }
    })(),
  );
});

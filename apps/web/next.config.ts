import type { NextConfig } from "next";

// The showcase build (NEXT_PUBLIC_DEMO=1, e.g. on Vercel) has no backend: the read-only API
// calls are answered from a snapshot of one book in public/demo (scripts/export_showcase.py).
const DEMO_ROUTES = [
  ["/api/health", "/demo/health.json"],
  ["/api/documents", "/demo/documents.json"],
  ["/api/documents/:id/render", "/demo/documents/:id/render.json"],
  ["/api/documents/:id/chapters/:section/manifest", "/demo/documents/:id/chapters/:section/manifest.json"],
  ["/api/documents/:id/chapters/:section/audio", "/demo/documents/:id/chapters/:section/audio.mp3"],
  ["/api/tts/voices", "/demo/tts/voices.json"],
  ["/api/documents/:id", "/demo/documents/:id.json"],
];

const nextConfig: NextConfig = {
  // Proxy /api/* to the FastAPI service so the browser only talks to one origin:
  // no CORS setup, and the API URL lives in one place.
  async rewrites() {
    if (process.env.NEXT_PUBLIC_DEMO === "1") {
      return DEMO_ROUTES.map(([source, destination]) => ({ source, destination }));
    }
    const apiUrl = process.env.API_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }];
  },
  cacheComponents: true,
  experimental: {
    // The proxy gives up after 30 s by default; packaging a long book as an M4B takes longer
    proxyTimeout: 5 * 60_000,
  },
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;

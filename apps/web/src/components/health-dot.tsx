"use client";

import { useEffect, useState } from "react";

type State = "checking" | "online" | "degraded" | "offline";

const LABELS: Record<State, string> = {
  checking: "Connecting…",
  online: "Studio online",
  degraded: "Database offline",
  offline: "API offline",
};

const DOT: Record<State, string> = {
  checking: "bg-ink-faint",
  online: "bg-tungsten shadow-[0_0_10px_rgb(255_181_71/0.8)]",
  degraded: "bg-danger",
  offline: "bg-danger",
};

// Small status light showing whether the backend (and its database) is reachable.
export function HealthDot() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    // /api/* is proxied to FastAPI by the rewrite in next.config.ts
    fetch("/api/health")
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((body: { database: boolean }) => setState(body.database ? "online" : "degraded"))
      .catch(() => setState("offline"));
  }, []);

  return (
    <span role="status" aria-label={LABELS[state]} className="flex items-center gap-2 font-mono text-xs text-ink-muted">
      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${DOT[state]}`} />
      {/* On phones the nav is tight: the dot alone carries the state */}
      <span aria-hidden className="hidden md:inline">
        {LABELS[state]}
      </span>
    </span>
  );
}

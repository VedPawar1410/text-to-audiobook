"use client";

import { useEffect, useState } from "react";

type Health = { status: string; database: boolean };

export function HealthStatus() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    // /api/* is proxied to FastAPI by the rewrite in next.config.ts
    fetch("/api/health")
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  if (error) return <Row label="API" ok={false} />;
  if (!health) return <p className="text-zinc-500">Checking…</p>;

  return (
    <div className="flex flex-col gap-2">
      <Row label="API" ok />
      <Row label="Database" ok={health.database} />
    </div>
  );
}

function Row({ label, ok }: { label: string; ok: boolean }) {
  return (
    <p className="flex items-center gap-3 font-mono text-sm">
      <span className={`h-2 w-2 rounded-full ${ok ? "bg-emerald-400" : "bg-rose-500"}`} />
      {label}: {ok ? "connected" : "unreachable"}
    </p>
  );
}

import { HealthStatus } from "./health-status";

// Placeholder home: proves web → API → database are wired up.
// The real UI (design system, New / Director's Notes / Reader) lands in later PRs.
export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 bg-zinc-950 px-6 text-zinc-50">
      <h1 className="text-5xl font-semibold tracking-tight">text-to-audiobook</h1>
      <p className="text-zinc-400">Scaffold check</p>
      <HealthStatus />
    </main>
  );
}

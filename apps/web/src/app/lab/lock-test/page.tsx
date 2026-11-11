import type { Metadata } from "next";
import { LockTest } from "@/components/lab/lock-test";
import { Eyebrow } from "@/components/ui";

// A hidden test page (not in the nav) for the iPhone audio test in the PWA plan
export const metadata: Metadata = { title: "Lock test · Narrate", robots: { index: false } };

export default function LockTestPage() {
  return (
    <main className="mx-auto w-full max-w-2xl px-4 pt-32 pb-24 md:px-8 md:pt-40">
      <Eyebrow>Lab</Eyebrow>
      <h1 className="mt-5 font-display text-4xl font-light tracking-tight md:text-5xl">Does audio survive the lock screen?</h1>
      <p className="mt-4 text-ink-muted">
        Measures how much audio plays while the phone is locked, in a Safari tab and as a Home Screen app.
      </p>
      <div className="mt-10">
        <LockTest />
      </div>
    </main>
  );
}

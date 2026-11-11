import type { Metadata } from "next";
import { OfflineTest } from "@/components/lab/offline-test";
import { Eyebrow } from "@/components/ui";

// A hidden test page for the airplane-mode audio test in the PWA plan
export const metadata: Metadata = { title: "Offline test · Narrate", robots: { index: false } };

export default function OfflineTestPage() {
  return (
    <main className="mx-auto w-full max-w-2xl px-4 pt-32 pb-24 md:px-8 md:pt-40">
      <Eyebrow>Lab</Eyebrow>
      <h1 className="mt-5 font-display text-4xl font-light tracking-tight md:text-5xl">Does a saved book play offline?</h1>
      <div className="mt-10">
        <OfflineTest />
      </div>
    </main>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import { Library } from "@/components/library";
import { Eyebrow } from "@/components/ui";

export const metadata: Metadata = { title: "Library · Narrate" };

export default function LibraryPage() {
  return (
    <main className="mx-auto w-full max-w-5xl px-4 pt-32 pb-24 md:px-8 md:pt-40">
      <Eyebrow>Library</Eyebrow>
      <h1 className="mt-5 font-display text-4xl font-light tracking-tight md:text-6xl">Your books</h1>
      <div className="mt-10">
        <Library />
      </div>
      {/* Temporary: the installed app has no address bar. Removed once offline books ship (P3.3). */}
      <Link href="/lab/offline-test" className="mt-16 inline-block text-xs text-ink-faint">
        Lab: offline test
      </Link>
    </main>
  );
}

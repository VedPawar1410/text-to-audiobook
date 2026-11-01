import type { Metadata } from "next";
import Link from "next/link";
import { PillLink, SECONDARY } from "@/components/pill-link";
import { Reveal } from "@/components/reveal";
import { Eyebrow } from "@/components/ui";

export const metadata: Metadata = { title: "Not found · Narrate" };

export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-4 pt-32 pb-24 md:px-8 md:pt-40">
      <Reveal>
        <Eyebrow>404</Eyebrow>
        <h1 className="mt-5 font-display text-4xl leading-[1.05] font-light tracking-tight md:text-6xl">
          This page isn&apos;t in the <em className="text-tungsten">script</em>.
        </h1>
        <p className="mt-4 max-w-xl text-lg leading-relaxed text-ink-muted">
          The link may be out of date, or the book was deleted.
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-2">
          <PillLink href="/documents" icon="right">
            Go to your library
          </PillLink>
          <Link href="/new" className={SECONDARY}>
            Start a new book
          </Link>
        </div>
      </Reveal>
    </main>
  );
}

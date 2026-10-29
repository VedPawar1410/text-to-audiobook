import type { Metadata } from "next";
import { NewDocument } from "@/components/new/new-document";
import { Reveal } from "@/components/reveal";
import { Eyebrow } from "@/components/ui";

export const metadata: Metadata = { title: "New book · Narrate" };

export default function NewPage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-4 pt-32 pb-24 md:px-8 md:pt-40">
      <Reveal>
        <Eyebrow>New book</Eyebrow>
        <h1 className="mt-5 font-display text-4xl leading-[1.05] font-light tracking-tight md:text-6xl">
          What should we <em className="text-tungsten">perform</em>?
        </h1>
        <p className="mt-4 max-w-xl text-lg leading-relaxed text-ink-muted">
          Bring a script, a chapter, an article or a whole book. There&apos;s no length limit.
        </p>
      </Reveal>
      <Reveal delay={0.15} className="mt-10">
        <NewDocument />
      </Reveal>
    </main>
  );
}

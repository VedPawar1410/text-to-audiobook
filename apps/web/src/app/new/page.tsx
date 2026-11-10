import type { Metadata } from "next";
import { Bezel } from "@/components/bezel";
import { NewDocument } from "@/components/new/new-document";
import { PillLink } from "@/components/pill-link";
import { Reveal } from "@/components/reveal";
import { Eyebrow } from "@/components/ui";
import { DEMO, DEMO_MESSAGE, REPO_URL } from "@/lib/demo";

// In the showcase build there's no API to import into: explain, and offer the recorded book
function ShowcaseNotice() {
  return (
    <Bezel>
      <div className="flex flex-col items-start gap-6 p-8 md:p-12">
        <p className="max-w-xl text-lg leading-relaxed text-ink-muted">{DEMO_MESSAGE}</p>
        <div className="flex flex-wrap gap-3">
          <PillLink href="/documents" icon="right">
            Listen to the recorded book
          </PillLink>
          <a href={REPO_URL} target="_blank" rel="noopener" className="flex min-h-11 items-center rounded-full border border-hairline px-5 text-sm text-ink-muted hover:text-ink">
            Get the code on GitHub ↗
          </a>
        </div>
      </div>
    </Bezel>
  );
}

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
        {DEMO ? <ShowcaseNotice /> : <NewDocument />}
      </Reveal>
    </main>
  );
}

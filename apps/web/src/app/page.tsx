import { Bezel } from "@/components/bezel";
import { HeroStage } from "@/components/hero-stage";
import { PillLink, SECONDARY } from "@/components/pill-link";
import { Reveal } from "@/components/reveal";

const STEPS = [
  {
    n: "01",
    title: "Bring any text",
    body: "Paste a script, drop a PDF, or link an article. There's no length limit, so whole books are fine.",
  },
  {
    n: "02",
    title: "The director reads it first",
    body: "AI works out the genre, the structure, who's speaking, and how every line should land.",
  },
  {
    n: "03",
    title: "Listen and read along",
    body: "A full cast performs it. Every word lights up as it's spoken, and you can pause to ask about anything.",
  },
];

const INPUTS = ["Paste text", ".txt", ".md", "PDF", "Web link", "Screenplays"];

export default function Home() {
  return (
    <main>
      <section className="mx-auto grid min-h-[100dvh] max-w-6xl items-center gap-x-12 gap-y-10 px-4 pt-32 pb-16 md:grid-cols-12 md:px-8">
        <div className="md:col-span-7">
          <Reveal>
            <span className="inline-block rounded-full border border-hairline px-3 py-1 font-mono text-[10px] tracking-[0.2em] text-ink-muted uppercase">
              AI audiobook studio
            </span>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 className="mt-6 font-display text-5xl leading-[0.95] font-light tracking-tight md:text-7xl">
              Every story deserves <em className="text-tungsten">a voice.</em>
            </h1>
          </Reveal>
          <Reveal delay={0.2}>
            <p className="mt-6 max-w-[34rem] text-lg leading-relaxed text-ink-muted">
              Paste a script, an article or a whole book. An AI director reads it, casts a voice
              for every character and performs it, while you read along word by word.
            </p>
          </Reveal>
          <Reveal delay={0.3} className="mt-10 flex flex-wrap items-center gap-2">
            <PillLink href="/new" icon="right">
              Start a new book
            </PillLink>
            <a href="#how" className={SECONDARY}>
              See how it works
            </a>
          </Reveal>
        </div>

        <HeroStage />
      </section>

      <section id="how" className="mx-auto max-w-6xl scroll-mt-24 px-4 py-24 md:px-8 md:py-40">
        <Reveal>
          <h2 className="max-w-xl font-display text-4xl leading-tight font-light tracking-tight md:text-5xl">
            From page to performance in three acts.
          </h2>
        </Reveal>

        <div className="mt-14 grid gap-6 md:grid-cols-12">
          {STEPS.map((step, i) => (
            <Reveal
              key={step.n}
              delay={i * 0.1}
              className={i === 0 ? "md:col-span-7 md:row-span-2" : "md:col-span-5"}
            >
              <Bezel className="h-full">
                <div className="flex h-full flex-col justify-between gap-10 p-8 md:p-10">
                  <span className="font-mono text-xs tracking-[0.2em] text-tungsten">{step.n}</span>
                  {i === 0 && (
                    <ul aria-label="Supported inputs" className="flex flex-wrap gap-2">
                      {INPUTS.map((input) => (
                        <li
                          key={input}
                          className="rounded-full border border-hairline px-4 py-2 font-mono text-xs text-ink-muted"
                        >
                          {input}
                        </li>
                      ))}
                    </ul>
                  )}
                  <div>
                    <h3 className="font-display text-2xl tracking-tight md:text-3xl">{step.title}</h3>
                    <p className="mt-3 max-w-md leading-relaxed text-ink-muted">{step.body}</p>
                  </div>
                </div>
              </Bezel>
            </Reveal>
          ))}
        </div>
      </section>

      <footer className="mx-auto w-full max-w-6xl border-t border-hairline px-4 py-10 font-mono text-xs text-ink-muted md:px-8">
        Early proof of concept · built in public
      </footer>
    </main>
  );
}

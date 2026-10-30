import type { ReactNode } from "react";

/** Small mono label above a heading, as in the design system. */
export function Eyebrow({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={`inline-block rounded-full border border-hairline px-3 py-1 font-mono text-[10px] tracking-[0.2em] text-ink-muted uppercase ${className}`}
    >
      {children}
    </span>
  );
}

export const LABEL = "font-mono text-[11px] tracking-[0.2em] text-ink-muted uppercase";

export const SELECT =
  "min-h-11 w-full cursor-pointer rounded-2xl border border-hairline bg-stage px-3 text-sm text-ink transition-colors duration-300 ease-spring hover:border-ink/20 disabled:cursor-wait disabled:opacity-50";

export function ErrorNote({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} role="alert" className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
      {children}
    </p>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-[2rem] bg-ink/[0.04] ${className}`} />;
}

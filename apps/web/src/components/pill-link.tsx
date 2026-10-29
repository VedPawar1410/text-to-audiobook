import type { ReactNode } from "react";

// Primary CTA: a tungsten pill with its icon nested in its own circle ("button in button").
export function PillLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      className="group inline-flex min-h-11 cursor-pointer items-center gap-3 rounded-full bg-tungsten py-1.5 pr-1.5 pl-6 font-medium text-on-tungsten transition-transform duration-300 ease-spring active:scale-[0.98]"
    >
      {children}
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-on-tungsten/10 transition-transform duration-500 ease-spring group-hover:translate-y-0.5 group-hover:scale-105">
        <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.25">
          <path d="M8 3v10M3.5 8.5 8 13l4.5-4.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </a>
  );
}

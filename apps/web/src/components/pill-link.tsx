import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

// Primary CTA: a tungsten pill with its icon nested in its own circle ("button in button").
const PILL =
  "group inline-flex min-h-11 cursor-pointer items-center gap-3 rounded-full bg-tungsten py-1.5 pr-1.5 pl-6 font-medium text-on-tungsten transition-[transform,opacity] duration-300 ease-spring active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50";

const ICONS = {
  down: "M8 3v10M3.5 8.5 8 13l4.5-4.5",
  right: "M3 8h10M8.5 3.5 13 8l-4.5 4.5",
};

function PillIcon({ icon, busy = false }: { icon: keyof typeof ICONS; busy?: boolean }) {
  const nudge = icon === "down" ? "group-hover:translate-y-0.5" : "group-hover:translate-x-0.5";
  return (
    <span
      className={`flex h-8 w-8 items-center justify-center rounded-full bg-on-tungsten/10 transition-transform duration-500 ease-spring group-hover:scale-105 ${nudge}`}
    >
      {busy ? (
        <span aria-hidden className="h-3.5 w-3.5 animate-spin rounded-full border border-on-tungsten/30 border-t-on-tungsten" />
      ) : (
        <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.25">
          <path d={ICONS[icon]} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
    </span>
  );
}

type PillLinkProps = { href: string; children: ReactNode; icon?: keyof typeof ICONS };

export function PillLink({ href, children, icon = "down" }: PillLinkProps) {
  // In-page anchors stay plain links; routes use Next's client-side navigation
  const Component = href.startsWith("#") ? "a" : Link;
  return (
    <Component href={href} className={PILL}>
      {children}
      <PillIcon icon={icon} />
    </Component>
  );
}

type PillButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { busy?: boolean };

export function PillButton({ children, busy = false, disabled, ...props }: PillButtonProps) {
  return (
    <button {...props} disabled={disabled || busy} aria-busy={busy} className={PILL}>
      {children}
      <PillIcon icon="right" busy={busy} />
    </button>
  );
}

/** Quiet secondary action next to a pill. */
export const SECONDARY =
  "inline-flex min-h-11 cursor-pointer items-center rounded-full px-5 text-sm text-ink-muted transition-colors duration-300 ease-spring hover:bg-hairline hover:text-ink";

import Link from "next/link";
import { HealthDot } from "./health-dot";

const LINK =
  "flex min-h-11 items-center rounded-full px-3 text-sm text-ink-muted transition-colors duration-300 ease-spring hover:bg-hairline hover:text-ink sm:px-4";

// Floating "island" nav: a glass pill detached from the top edge.
// backdrop-blur is fine here because the nav is fixed (it never scrolls).
export function Nav() {
  return (
    <header className="fixed inset-x-0 top-4 z-30 flex justify-center px-4 md:top-6">
      <nav className="flex items-center gap-2 rounded-full border border-hairline bg-stage/70 py-1 pr-1 pl-5 backdrop-blur-xl sm:gap-3">
        <Link href="/" className="flex min-h-11 items-center font-display text-lg italic tracking-tight">
          Narrate
        </Link>
        <span aria-hidden className="h-4 w-px bg-hairline" />
        <HealthDot />
        <Link href="/new" className={LINK}>
          New
        </Link>
        <Link href="/documents" className={LINK}>
          Library
        </Link>
      </nav>
    </header>
  );
}

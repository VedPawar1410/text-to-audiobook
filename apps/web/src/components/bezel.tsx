import type { ReactNode } from "react";

// "Double bezel" card: a hairline outer shell holding an inner core with its own
// top highlight, so panels read like glass set into a machined tray.
export function Bezel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-[2rem] border border-hairline bg-ink/[0.03] p-1.5 ${className}`}>
      <div className="h-full rounded-[calc(2rem-0.375rem)] bg-stage-raised shadow-[inset_0_1px_0_rgb(244_237_226/0.06)]">
        {children}
      </div>
    </div>
  );
}

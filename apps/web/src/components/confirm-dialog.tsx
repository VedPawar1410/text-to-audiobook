"use client";

import { type ReactNode, useEffect, useRef } from "react";
import { SECONDARY } from "@/components/pill-link";

type Props = {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  busyLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

/**
 * A destructive-action confirmation on the native <dialog>: showModal() gives focus
 * trapping, Escape to close and an inert page behind it, with no library.
 * Cancel gets focus first, so an accidental Enter never destroys anything.
 */
export function ConfirmDialog({ open, title, children, confirmLabel, busyLabel, busy = false, onConfirm, onCancel }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);

  return (
    <dialog
      ref={dialog}
      aria-labelledby="confirm-title"
      onCancel={(event) => {
        event.preventDefault(); // Escape: React state decides when it closes
        if (!busy) onCancel();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget && !busy) onCancel(); // a click on the backdrop
      }}
      className="confirm-dialog m-auto w-[min(28rem,calc(100vw-2rem))] rounded-[2rem] border border-hairline bg-stage p-1.5 text-ink"
    >
      <div className="rounded-[calc(2rem-0.375rem)] bg-stage-raised p-6 shadow-[inset_0_1px_0_rgb(244_237_226/0.06)] md:p-8">
        <h2 id="confirm-title" className="font-display text-2xl tracking-tight">
          {title}
        </h2>
        <div className="mt-3 text-sm leading-relaxed text-ink-muted">{children}</div>
        <div className="mt-8 flex flex-wrap justify-end gap-2">
          <button type="button" autoFocus onClick={onCancel} disabled={busy} className={SECONDARY}>
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            aria-busy={busy}
            className="inline-flex min-h-11 cursor-pointer items-center rounded-full bg-danger px-5 text-sm font-medium text-stage transition-[transform,opacity] duration-300 ease-spring active:scale-[0.98] disabled:cursor-wait disabled:opacity-60"
          >
            {busy ? busyLabel : confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}

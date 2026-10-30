"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { LABEL } from "@/components/ui";
import { askStream, type AskTurn } from "@/lib/api";

export type AskContext = { selection: string | null; segmentId: number | null };

const ABOUT_SELECTION = ["What does this mean?", "Why does this matter here?", "Explain the reference"];
const ABOUT_POSITION = ["What's happening right now?", "Who are the characters so far?", "Summarise this scene"];

/** Side panel on desktop, bottom sheet on phones. Each opening starts a fresh conversation. */
export function AskPanel({ documentId, context, onClose }: { documentId: string; context: AskContext | null; onClose: () => void }) {
  const reduce = useReducedMotion();
  return (
    <AnimatePresence>
      {context && (
        <motion.aside
          key={`${context.segmentId}:${context.selection}`}
          role="dialog"
          aria-label="Ask about the text"
          initial={reduce ? false : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduce ? undefined : { opacity: 0, y: 24 }}
          transition={{ duration: 0.35, ease: [0.32, 0.72, 0, 1] }}
          className="fixed inset-x-0 bottom-0 z-40 flex max-h-[80dvh] flex-col rounded-t-[1.75rem] border border-hairline bg-stage-raised/95 backdrop-blur-xl md:inset-x-auto md:top-24 md:right-6 md:bottom-40 md:max-h-none md:w-[26rem] md:rounded-[1.75rem]"
        >
          <Conversation documentId={documentId} context={context} onClose={onClose} />
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function Conversation({ documentId, context, onClose }: { documentId: string; context: AskContext; onClose: () => void }) {
  const [turns, setTurns] = useState<AskTurn[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    input.current?.focus();
  }, []);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "end" });
  }, [turns]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function ask(text: string) {
    const asked = text.trim();
    if (!asked || busy) return;
    const history = turns;
    setQuestion("");
    setError(null);
    setBusy(true);
    setTurns([...history, { role: "user", text: asked }, { role: "assistant", text: "" }]);
    try {
      const body = { question: asked, selection: context.selection, segment_id: context.segmentId, history };
      for await (const chunk of askStream(documentId, body)) {
        // Append each piece to the answer being written
        setTurns((all) => [...all.slice(0, -1), { role: "assistant", text: all[all.length - 1].text + chunk }]);
      }
    } catch (e) {
      setError((e as Error).message);
      setTurns(history);
      setQuestion(asked);
    } finally {
      setBusy(false);
    }
  }

  const suggestions = context.selection ? ABOUT_SELECTION : ABOUT_POSITION;

  return (
    <>
      <header className="flex items-center justify-between gap-3 border-b border-hairline py-2 pr-2 pl-5">
        <p className={LABEL}>Ask about the text</p>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-full text-ink-muted hover:bg-hairline hover:text-ink"
        >
          <svg aria-hidden viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round">
            <path d="m4 4 8 8M12 4l-8 8" />
          </svg>
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {context.selection && (
          <blockquote className="mb-4 line-clamp-4 border-l-2 border-tungsten/60 pl-3 font-read text-ink-muted italic">
            &ldquo;{context.selection}&rdquo;
          </blockquote>
        )}
        {turns.length === 0 && (
          <ul className="flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <li key={suggestion}>
                <button
                  type="button"
                  onClick={() => void ask(suggestion)}
                  className="min-h-11 cursor-pointer rounded-full border border-hairline px-4 text-sm transition-colors hover:border-tungsten/50"
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        )}
        <div aria-live="polite" className="flex flex-col gap-4">
          {turns.map((turn, i) =>
            turn.role === "user" ? (
              <p key={i} className="ml-10 self-end rounded-2xl bg-ink/[0.06] px-4 py-2 text-sm">
                {turn.text}
              </p>
            ) : (
              <p key={i} className="font-read text-lg leading-relaxed whitespace-pre-wrap">
                {turn.text || <span className="text-ink-muted">Thinking…</span>}
              </p>
            ),
          )}
        </div>
        {error && (
          <p role="alert" className="mt-3 text-sm text-danger">
            {error}
          </p>
        )}
        <div ref={end} />
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask(question);
        }}
        className="flex items-end gap-2 border-t border-hairline p-3"
      >
        <label htmlFor="ask-input" className="sr-only">
          Your question
        </label>
        <textarea
          id="ask-input"
          ref={input}
          rows={1}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask(question);
            }
          }}
          placeholder="Ask anything about this…"
          className="max-h-32 min-h-11 flex-1 resize-none rounded-2xl border border-hairline bg-stage px-4 py-2.5 text-sm text-ink [field-sizing:content] placeholder:text-ink-faint"
        />
        <button
          type="submit"
          aria-label="Ask"
          disabled={busy || !question.trim()}
          className="flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full bg-tungsten text-on-tungsten transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
        >
          <svg aria-hidden viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 13V3M3.5 7.5 8 3l4.5 4.5" />
          </svg>
        </button>
      </form>
    </>
  );
}

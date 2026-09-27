"use client";

import { useState } from "react";
import { askAssistant } from "@/lib/api";
import { splitChatAnswer } from "@/lib/chatAnswer";
import { UTILITY_A, UTILITY_B } from "@/lib/config";
import type { AssistantMessage } from "@/lib/types";

interface Props {
  opportunityId: string | null;
  docked?: boolean;
}

interface Failure {
  query: string;
  message: string;
}

function AssistantAnswer({ content }: { content: string }) {
  const blocks = splitChatAnswer(content);
  return (
    <div className="text-sm [overflow-wrap:anywhere]">
      {blocks.map((block, index) => {
        const lead = index === 0;
        if (block.kind === "heading") {
          return (
            <div key={index}>
              {lead && <p className="font-semibold">GridSync:</p>}
              <h3 className={`${lead ? "mt-1" : "mt-3"} font-display text-base font-semibold`}>{block.text}</h3>
            </div>
          );
        }
        return (
          <p key={index} className={`${lead ? "" : "mt-1"} whitespace-pre-wrap`}>
            {lead && <span className="font-semibold">GridSync: </span>}
            {block.text}
          </p>
        );
      })}
    </div>
  );
}

export default function ChatPanel({ opportunityId, docked = false }: Props) {
  const [turns, setTurns] = useState<AssistantMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [open, setOpen] = useState(false);

  async function send(query: string) {
    const text = query.trim();
    if (!text || pending) return;
    setFailure(null);
    setPending(text);
    setDraft("");
    try {
      const result = await askAssistant({
        query: text,
        messages: turns,
        utility_a: UTILITY_A,
        utility_b: UTILITY_B,
        ...(opportunityId ? { opportunity_id: opportunityId } : {}),
      });
      setTurns((current) => [
        ...current,
        { role: "user", content: text },
        { role: "assistant", content: result.answer },
      ]);
    } catch (e) {
      setFailure({
        query: text,
        message: e instanceof Error ? e.message : "The assistant request failed.",
      });
      setDraft(text);
    } finally {
      setPending(null);
    }
  }

  return (
    <section
      className={`shrink-0 border-t border-rule bg-sheet ${docked ? "lg:flex lg:h-full lg:min-h-0 lg:flex-col lg:border-t-0" : ""}`}
      aria-label="Analysis chat"
    >
      <h2 className="hidden shrink-0 px-4 pt-3 font-display text-lg font-semibold sm:block">Ask about the analysis</h2>
      <button
        type="button"
        className="flex min-h-11 w-full shrink-0 items-center justify-between gap-3 px-4 py-3 text-left font-display text-lg font-semibold sm:hidden"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        Ask about the analysis
        <span className="text-sm font-semibold text-cyan">{open ? "Hide" : "Show"}</span>
      </button>
      <div className={`${open ? "flex flex-col" : "hidden sm:block"} ${docked ? "lg:flex lg:min-h-0 lg:flex-1 lg:flex-col" : ""}`}>
      <p className="shrink-0 px-4 text-sm text-graphite sm:pt-0">
        {opportunityId
          ? "This conversation is only about the open pair."
          : "This conversation is about the ranked pairs, not one open card."}
      </p>

      <div
        className={`max-h-none space-y-3 overflow-visible px-4 py-3 break-words sm:max-h-44 sm:overflow-y-auto ${docked ? "lg:max-h-none lg:min-h-0 lg:flex-1 lg:overflow-y-auto" : ""}`}
        aria-live="polite"
      >
        {turns.length === 0 && !pending && !failure && (
          <p className="text-sm text-graphite">Answers come from the analysis record. The chat does not rescore pairs.</p>
        )}
        {turns.map((turn, index) =>
          turn.role === "user" ? (
            <p key={`${turn.role}-${index}`} className="text-sm whitespace-pre-wrap [overflow-wrap:anywhere]">
              <span className="font-semibold">You: </span>
              {turn.content}
            </p>
          ) : (
            <AssistantAnswer key={`${turn.role}-${index}`} content={turn.content} />
          ),
        )}
        {pending && (
          <p className="text-sm" role="status">
            <span className="font-semibold">You: </span>
            {pending}
            <span className="mt-1 block text-graphite">Looking up the analysis record…</span>
          </p>
        )}
        {failure && (
          <p className="text-sm">
            {failure.message}{" "}
            <button type="button" onClick={() => send(failure.query)} className="font-semibold underline">
              Try again
            </button>
          </p>
        )}
      </div>

      <form
        className="flex shrink-0 gap-2 border-t border-rule px-4 py-3"
        onSubmit={(event) => {
          event.preventDefault();
          void send(draft);
        }}
      >
        <label className="sr-only" htmlFor="gridsync-chat">
          Question
        </label>
        <input
          id="gridsync-chat"
          value={draft}
          maxLength={1000}
          disabled={pending !== null}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={opportunityId ? "Why did this pair match?" : "Which pairs are strongest?"}
          className="min-h-11 min-w-0 flex-1 rounded-full border border-rule bg-paper px-3 py-1.5 text-sm text-ink disabled:opacity-60 sm:min-h-0"
        />
        <button
          type="submit"
          disabled={pending !== null || draft.trim() === ""}
          className="min-h-11 shrink-0 rounded-full bg-cyan px-4 py-1.5 font-display font-semibold text-paper disabled:cursor-wait disabled:opacity-60 sm:min-h-0 sm:px-3"
        >
          {pending ? "Asking…" : "Ask"}
        </button>
      </form>
      </div>
    </section>
  );
}

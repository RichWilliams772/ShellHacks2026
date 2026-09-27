"use client";

import { useState } from "react";
import { askAssistant } from "@/lib/api";
import { UTILITY_A, UTILITY_B } from "@/lib/config";
import type { AssistantMessage } from "@/lib/types";

interface Props {
  opportunityId: string | null;
}

interface Failure {
  query: string;
  message: string;
}

export default function ChatPanel({ opportunityId }: Props) {
  const [turns, setTurns] = useState<AssistantMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);

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
    <section className="shrink-0 border-t border-ink bg-sheet" aria-label="Analysis chat">
      <div className="px-4 pt-3">
        <h2 className="font-display text-lg font-semibold">Ask about the analysis</h2>
        <p className="text-sm text-graphite">
          {opportunityId
            ? "This conversation is only about the open pair."
            : "This conversation is about the ranked pairs, not one open card."}
        </p>
      </div>

      <div className="max-h-44 space-y-3 overflow-y-auto px-4 py-3" aria-live="polite">
        {turns.length === 0 && !pending && !failure && (
          <p className="text-sm text-graphite">Answers come from the analysis record. The chat does not rescore pairs.</p>
        )}
        {turns.map((turn, index) => (
          <p key={`${turn.role}-${index}`} className="whitespace-pre-wrap text-sm">
            <span className="font-semibold">{turn.role === "user" ? "You" : "GridSync"}: </span>
            {turn.content}
          </p>
        ))}
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
        className="flex gap-2 border-t border-rule px-4 py-3"
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
          className="min-w-0 flex-1 rounded-sm border border-rule bg-paper px-2 py-1.5 text-sm disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={pending !== null || draft.trim() === ""}
          className="rounded-sm bg-ink px-3 py-1.5 font-display font-semibold text-paper disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "Asking…" : "Ask"}
        </button>
      </form>
    </section>
  );
}

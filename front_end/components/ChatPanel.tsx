"use client";

import { useState } from "react";
import { askAssistant } from "@/lib/api";
import { UTILITY_A, UTILITY_B } from "@/lib/config";
import type { AssistantMessage, AssistantSource } from "@/lib/types";

interface Props {
  opportunityId: string | null;
  // Shown under the title when a pair is open, e.g. "Duke P-0288 <-> TECO 66833".
  contextLabel?: string;
  // Clicking one asks it immediately. Differs by whether a pair is open (Dashboard
  // decides the wording); this component only renders and sends them.
  suggestions: string[];
}

// sources is UI-only: never sent back to the backend, which rejects unknown
// fields on a chat turn.
interface ChatTurn extends AssistantMessage {
  sources?: AssistantSource[];
}

interface Failure {
  query: string;
  message: string;
}

function SourceList({ sources }: { sources: AssistantSource[] }) {
  if (sources.length === 0) return null;
  return (
    <ul className="mt-1.5 space-y-0.5 border-l-2 border-rule pl-2 text-xs text-graphite">
      {sources.map((s, i) => (
        <li key={i}>
          {s.document_title} — p. {s.page}
        </li>
      ))}
    </ul>
  );
}

export default function ChatPanel({ opportunityId, contextLabel, suggestions }: Props) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
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
        messages: turns.map(({ role, content }) => ({ role, content })),
        utility_a: UTILITY_A,
        utility_b: UTILITY_B,
        ...(opportunityId ? { opportunity_id: opportunityId } : {}),
      });
      setTurns((current) => [
        ...current,
        { role: "user", content: text },
        { role: "assistant", content: result.answer, sources: result.sources },
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
    <section className="flex h-full min-h-0 flex-col bg-sheet" aria-label="Analysis chat">
      <div className="px-4 pt-3">
        <h2 className="font-display text-lg font-semibold">GridSync Assistant</h2>
        <p className="text-sm text-graphite">{contextLabel ? `Context: ${contextLabel}` : "Grounded planning insights"}</p>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3" aria-live="polite">
        {turns.length === 0 && !pending && !failure && (
          <div className="space-y-3">
            <p className="text-sm text-graphite">
              Ask about GridSync opportunities, project comparisons, or the source planning documents. Answers
              come from the analysis record and cited filings - the chat does not rescore pairs.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void send(s)}
                  className="rounded-full border border-rule px-3 py-1 text-left text-xs hover:border-ink hover:bg-rule"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((turn, index) => (
          <div key={`${turn.role}-${index}`} className="text-sm">
            <p className="whitespace-pre-wrap">
              <span className="font-semibold">{turn.role === "user" ? "You" : "GridSync"}: </span>
              {turn.content}
            </p>
            {turn.role === "assistant" && turn.sources && <SourceList sources={turn.sources} />}
          </div>
        ))}
        {pending && (
          <p className="text-sm" role="status">
            <span className="font-semibold">You: </span>
            {pending}
            <span className="mt-1 flex items-center gap-2 text-graphite">
              <span className="h-1.5 w-1.5 shrink-0 animate-pulse bg-graphite motion-reduce:animate-none" aria-hidden />
              Reviewing GridSync data…
            </span>
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
          placeholder="Ask GridSync about these projects…"
          className="min-w-0 flex-1 rounded-lg border border-rule bg-paper px-3 py-1.5 text-sm disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={pending !== null || draft.trim() === ""}
          className="flex items-center gap-2 rounded-lg bg-ink px-3.5 py-1.5 font-display font-semibold text-paper disabled:cursor-wait disabled:opacity-60"
        >
          {pending && <span className="h-1.5 w-1.5 shrink-0 animate-pulse bg-paper motion-reduce:animate-none" aria-hidden />}
          {pending ? "Asking" : "Ask"}
        </button>
      </form>
    </section>
  );
}

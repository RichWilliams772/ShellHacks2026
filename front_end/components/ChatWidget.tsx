"use client";

import { useState } from "react";
import type { Opportunity } from "@/lib/types";
import ChatPanel from "./ChatPanel";

interface Props {
  // The open pair, if any. Chat still works dashboard-wide with nothing selected.
  opportunity: Opportunity | null;
}

const GENERAL_SUGGESTIONS = [
  "Why is the top opportunity ranked highly?",
  "Which opportunities involve 230 kV projects?",
  "What does TECO's plan say about transmission upgrades?",
  "What does Coordination Score mean?",
];

function pairSuggestions(): string[] {
  return [
    "Why is this opportunity ranked highly?",
    "How do these project schedules compare?",
    "What potential resources were identified?",
    "What does the Storm Protection Plan say about this project?",
  ];
}

// Line-art icons drawn at the same weight as the map's dimension ticks, not emoji -
// the drafting theme has no place for a system emoji glyph.
function AssistantIcon({ open }: { open: boolean }) {
  if (open) {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
        <path d="M2.5 2.5l11 11M13.5 2.5l-11 11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="square" />
      </svg>
    );
  }
  return (
    <svg width="19" height="19" viewBox="0 0 20 18" fill="none" aria-hidden>
      <path d="M1.5 1.5h17v11H8.5l-4 4.5v-4.5h-3z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

export default function ChatWidget({ opportunity }: Props) {
  const [open, setOpen] = useState(false);

  const contextLabel = opportunity ? `${opportunity.project_a.id} ↔ ${opportunity.project_b.id}` : undefined;
  const suggestions = opportunity ? pairSuggestions() : GENERAL_SUGGESTIONS;

  return (
    <div className="absolute bottom-3 right-3 z-[1000] flex flex-col items-end gap-2">
      {open && (
        <div
          role="dialog"
          aria-label="GridSync Assistant"
          className="panel-in flex h-[min(560px,70vh)] w-[380px] max-w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-lg border border-ink bg-sheet shadow-[0_24px_48px_-20px_rgba(27,34,48,0.5)]"
        >
          <div className="flex shrink-0 items-center justify-between border-b border-ink px-3 py-1.5">
            <span className="text-xs font-semibold tracking-wide text-graphite uppercase">GridSync Assistant</span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close assistant chat"
              className="px-1 text-graphite hover:text-ink"
            >
              ✕
            </button>
          </div>
          <div className="min-h-0 flex-1">
            <ChatPanel
              key={opportunity?.opportunity_id ?? "all"}
              opportunityId={opportunity?.opportunity_id ?? null}
              contextLabel={contextLabel}
              suggestions={suggestions}
            />
          </div>
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? "Close GridSync Assistant" : "Open GridSync Assistant"}
        className="flex h-11 items-center gap-2 rounded-full border border-ink bg-ink px-5 text-paper shadow-[0_8px_20px_-6px_rgba(27,34,48,0.5)] transition-shadow hover:bg-redline hover:shadow-[0_10px_24px_-6px_rgba(200,53,43,0.5)]"
      >
        <AssistantIcon open={open} />
        <span className="font-display text-sm font-semibold">{open ? "Close" : "Assistant"}</span>
      </button>
    </div>
  );
}

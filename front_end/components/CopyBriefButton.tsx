"use client";

import { useEffect, useRef, useState } from "react";
import type { Opportunity } from "@/lib/types";
import { formatCoordinationBrief } from "@/lib/brief";

type Status = "idle" | "copied" | "failed";

// The caller mounts this keyed by opportunity_id (same pattern Dashboard.tsx already uses for
// ChatPanel) - switching pairs remounts the whole component, so `status` resets for free with
// no effect needed. Setting state directly from an effect just to mirror a prop is an
// anti-pattern React's own lint rule (react-hooks/set-state-in-effect) flags for exactly this
// reason: it costs an extra render for something the key can do for free.
export default function CopyBriefButton({ o }: { o: Opportunity }) {
  const [status, setStatus] = useState<Status>("idle");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const text = formatCoordinationBrief(o);

  // Only the success confirmation clears itself. A "failed" state must stay put - it's the
  // fallback UI (the selectable textarea below), and auto-clearing it would yank the text
  // away before the user has time to select and copy it by hand.
  useEffect(() => {
    if (status !== "copied") return;
    const id = setTimeout(() => setStatus("idle"), 2000);
    return () => clearTimeout(id);
  }, [status]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  }

  // When the fallback textarea appears, select its contents immediately - one fewer click
  // between "clipboard didn't work" and actually having the text selected.
  useEffect(() => {
    if (status === "failed") textareaRef.current?.select();
  }, [status]);

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={copy}
        className="rounded-sm border border-ink px-3 py-1.5 text-sm font-semibold hover:bg-rule"
      >
        {status === "copied" ? "✓ Brief copied" : "Copy Coordination Brief"}
      </button>
      {status === "failed" && (
        <div className="w-full text-right">
          <p className="text-sm text-graphite">Clipboard access isn&apos;t available here - select the text below and copy it manually.</p>
          <textarea
            ref={textareaRef}
            readOnly
            value={text}
            onFocus={(e) => e.currentTarget.select()}
            rows={6}
            className="mt-1 w-full resize-y rounded-sm border border-rule bg-paper p-2 text-left text-xs"
          />
        </div>
      )}
    </div>
  );
}

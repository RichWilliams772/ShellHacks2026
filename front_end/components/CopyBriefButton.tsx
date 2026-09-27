"use client";

import { useEffect, useState } from "react";
import type { Opportunity } from "@/lib/types";
import { formatCoordinationBrief } from "@/lib/brief";

type Status = "idle" | "copied" | "failed";

export default function CopyBriefButton({ o }: { o: Opportunity }) {
  const [status, setStatus] = useState<Status>("idle");

  // Confirmation clears itself; also clears on unmount (e.g. switching pairs) so a stale
  // "copied" state never lingers into a different opportunity's button.
  useEffect(() => {
    if (status === "idle") return;
    const id = setTimeout(() => setStatus("idle"), 2000);
    return () => clearTimeout(id);
  }, [status]);

  async function copy() {
    const text = formatCoordinationBrief(o);
    try {
      await navigator.clipboard.writeText(text);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-sm border border-ink px-3 py-1.5 text-sm font-semibold hover:bg-rule"
    >
      {status === "copied" ? "✓ Brief copied" : status === "failed" ? "Copy failed - select text manually" : "Copy Coordination Brief"}
    </button>
  );
}

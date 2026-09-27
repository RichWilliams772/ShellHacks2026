"use client";

import { useEffect, useState } from "react";
import type { Opportunity } from "@/lib/types";
import { downloadCoordinationBriefPdf } from "@/lib/pdf";

type Status = "idle" | "done" | "failed";

// Mounted keyed by opportunity_id (same pattern Dashboard.tsx uses elsewhere) - switching
// pairs remounts this component, so `status` resets for free with no effect needed.
export default function DownloadBriefButton({ o }: { o: Opportunity }) {
  const [status, setStatus] = useState<Status>("idle");

  useEffect(() => {
    if (status === "idle") return;
    const id = setTimeout(() => setStatus("idle"), 2000);
    return () => clearTimeout(id);
  }, [status]);

  function download() {
    try {
      downloadCoordinationBriefPdf(o);
      setStatus("done");
    } catch (e) {
      console.error("GridSync: PDF generation failed.", e);
      setStatus("failed");
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={download}
        className={`flex items-center gap-1.5 rounded-lg border px-3.5 py-1.5 text-sm font-semibold transition-colors ${
          status === "done" ? "border-ink bg-ink text-paper" : "border-ink hover:bg-rule"
        }`}
      >
        {status === "done" ? (
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M2.5 7.5l3 3 6-7" stroke="currentColor" strokeWidth="1.75" strokeLinecap="square" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M7 1v8m0 0L4 6m3 3l3-3M2 12h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
        {status === "done" ? "Brief downloaded" : "Download Coordination Brief"}
      </button>
      {status === "failed" && <p className="text-sm text-graphite">Couldn&apos;t generate the PDF - try again.</p>}
    </div>
  );
}

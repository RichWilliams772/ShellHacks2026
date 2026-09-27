"use client";

import { useState } from "react";
import { downloadOpportunityBrief, PDF_BRIEF_AVAILABLE } from "@/lib/api";

type Status = "idle" | "loading" | "error";

export default function DownloadBriefButton({ opportunityId }: { opportunityId: string }) {
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const loading = status === "loading";

  async function download() {
    if (!PDF_BRIEF_AVAILABLE || loading) return;
    setStatus("loading");
    setMessage("");
    try {
      await downloadOpportunityBrief(opportunityId);
      setStatus("idle");
    } catch (e) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "The PDF brief could not be downloaded.");
    }
  }

  return (
    <div className="flex min-w-0 flex-col items-stretch gap-1 sm:items-end">
      <button
        type="button"
        onClick={() => void download()}
        disabled={!PDF_BRIEF_AVAILABLE || loading}
        data-loading={loading ? "true" : "false"}
        aria-busy={loading}
        title={
          PDF_BRIEF_AVAILABLE ? undefined : "PDF brief download is not available from the analysis service yet."
        }
        className="gs-pdf min-h-11 w-full rounded-full bg-ink px-4 py-2 text-center font-display text-base font-semibold text-paper disabled:cursor-wait sm:min-h-0 sm:w-auto"
      >
        {loading ? "Downloading PDF…" : "Download PDF brief"}
      </button>
      {status === "error" && (
        <p className="max-w-full text-sm text-ink" role="alert">
          {message}
        </p>
      )}
    </div>
  );
}

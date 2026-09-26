import { API_URL, USE_MOCK } from "./config";
import type { AnalyzeRequest, AnalyzeResponse } from "./types";
// Snapshot of analyze_projects("Duke Energy Florida", "Tampa Electric") — real public data.
// Regenerate with the command in front_end/README.md after the data team updates the pipeline.
import snapshot from "./mock/analyze.json";

// Where the results came from, so the UI can say so. "fallback" = the live backend failed.
export type ResultSource = "snapshot" | "live" | "fallback";

// The backend returns analyze_projects() output as-is, so no field mapping happens here.
// The frontend never computes a score, distance, overlap, or resource.
export async function analyze(body: AnalyzeRequest): Promise<{ data: AnalyzeResponse; source: ResultSource }> {
  if (USE_MOCK) return { data: snapshot as AnalyzeResponse, source: "snapshot" };
  try {
    const res = await fetch(`${API_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Backend returned ${res.status} for /analyze`);
    const data = (await res.json()) as AnalyzeResponse;
    if (!Array.isArray(data?.opportunities) || !data.summary) throw new Error("Unexpected /analyze response shape");
    return { data, source: "live" };
  } catch (e) {
    // Keep the demo running on the saved results, but loudly: the UI flags it and the console has the cause.
    console.error("GridSync: live analysis failed, showing saved results instead.", e);
    return { data: snapshot as AnalyzeResponse, source: "fallback" };
  }
}

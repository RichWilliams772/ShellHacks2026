import { API_URL, USE_MOCK } from "./config";
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  AssistantQuery,
  AssistantResponse,
  AssistantSource,
  Opportunity,
  Project,
  SharedResource,
} from "./types";
// Snapshot of analyze_projects("Duke Energy Florida", "Tampa Electric") — real public data.
// Regenerate with the command in front_end/README.md after the data team updates the pipeline.
import snapshot from "./mock/analyze.json";

// Where the results came from, so the UI can say so. "fallback" = the live backend failed.
export type ResultSource = "snapshot" | "live" | "fallback";

// The backend does NOT return analyze_projects() output as-is — it reshapes the same
// underlying data (real evidence, real scores) into its own field names, closer to
// PROJECT_SPEC's canonical schema (project_name, latitude/longitude, voltage_kv, source_name…).
// mapAnalyzeResponse() is the one place that difference is absorbed, so every component
// downstream keeps working against lib/types.ts unchanged. Nothing here computes a score,
// distance, overlap, or resource — only renames/reshapes fields that already exist.

type RawProject = {
  id: string;
  utility: string;
  project_name: string;
  project_type: string;
  status?: string | null;
  voltage_label?: string | null;
  voltage_min_kv?: number | null;
  voltage_kv?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  estimated_in_service_year?: number | null;
  date_precision?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  from_latitude?: number | null;
  from_longitude?: number | null;
  to_latitude?: number | null;
  to_longitude?: number | null;
  geometry_type?: string | null;
  location_confidence?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  geography_source?: string | null;
  circuit_endpoint_source?: string | null;
  form1_schedule?: string | null;
};

type RawResource = {
  resource?: string;
  name?: string;
  label?: string;
  potential?: string;
  strength?: string;
  evidence?: string[];
  reason?: string;
};

type RawComponents = {
  geography_available?: boolean;
  geographic_score?: number | null;
  temporal_score?: number | null;
  text_similarity_score?: number | null;
  infrastructure_similarity?: number | null;
  score_confidence?: string | null;
  opportunity_rank?: number;
};

type RawOpportunity = {
  id: string;
  project_a: RawProject;
  project_b: RawProject;
  published_components?: RawComponents | null;
  features?: {
    distance_miles?: number | null;
    schedule_overlap_months?: number | null;
    temporal_precision?: string | null;
    year_difference?: number | null;
    same_active_year?: boolean | null;
  } | null;
  coordination_score: number;
  reasons?: string[];
  coordination_package?: { resources?: RawResource[] } | null;
  data_confidence?: Opportunity["data_confidence"] | null;
};

type RawAnalyzeResponse = {
  utility_a: string;
  utility_b: string;
  projects_analyzed: number;
  pairs_evaluated: number;
  opportunity_count: number;
  opportunities?: RawOpportunity[];
};

function asConfidence(value: string | null | undefined): Project["location_confidence"] {
  if (value === "HIGH" || value === "MEDIUM" || value === "LOW" || value === "UNKNOWN") return value;
  return null;
}

function asPotential(value: string | undefined): SharedResource["potential"] | null {
  if (value === "HIGH" || value === "MEDIUM" || value === "LOW") return value;
  return null;
}

function asDatePrecision(value: string | null | undefined): Project["date_precision"] {
  return value === "month" || value === "year" ? value : null;
}

function asGeometry(value: string | null | undefined): Project["geometry_type"] {
  return value === "approximate_corridor" || value === "point" ? value : null;
}

function voltageLabel(label: string | null, minKv: number | null, maxKv: number | null): string | null {
  if (label) return label;
  if (minKv == null || maxKv == null) return null;
  return minKv === maxKv ? `${minKv} kV` : `${minKv}-${maxKv} kV`;
}

function mapProject(raw: RawProject): Project {
  return {
    id: raw.id,
    utility: raw.utility,
    name: raw.project_name,
    project_type: raw.project_type,
    status: raw.status ?? null,
    voltage_label: voltageLabel(raw.voltage_label ?? null, raw.voltage_min_kv ?? null, raw.voltage_kv ?? null),
    start: raw.start_date ?? null,
    end: raw.end_date ?? null,
    in_service_year: raw.estimated_in_service_year ?? null,
    date_precision: asDatePrecision(raw.date_precision),
    mid_lat: raw.latitude ?? null,
    mid_lon: raw.longitude ?? null,
    from_lat: raw.from_latitude ?? null,
    from_lon: raw.from_longitude ?? null,
    to_lat: raw.to_latitude ?? null,
    to_lon: raw.to_longitude ?? null,
    geometry_type: asGeometry(raw.geometry_type),
    location_confidence: asConfidence(raw.location_confidence),
    // Only a citation the project actually has — never a placeholder for one it doesn't.
    sources: {
      ...(raw.source_name ? { project_source: raw.source_name } : {}),
      ...(raw.source_url ? { source_url: raw.source_url } : {}),
      ...(raw.geography_source ? { geography_source: raw.geography_source } : {}),
      ...(raw.circuit_endpoint_source ? { circuit_endpoint_source: raw.circuit_endpoint_source } : {}),
      ...(raw.form1_schedule ? { form1_schedule: raw.form1_schedule } : {}),
    },
  };
}

function mapResource(raw: RawResource): SharedResource | null {
  const potential = asPotential(raw.potential) ?? asPotential(raw.strength);
  if (!potential) return null;
  return {
    resource_id: raw.resource ?? raw.name ?? raw.label ?? "resource",
    display_name: raw.label ?? raw.name ?? raw.resource ?? "Resource",
    potential,
    evidence: raw.evidence ?? (raw.reason ? [raw.reason] : []),
  };
}

function mapOpportunity(raw: RawOpportunity): Opportunity {
  const c = raw.published_components ?? {};
  const f = raw.features ?? {};
  return {
    opportunity_id: raw.id,
    project_a: mapProject(raw.project_a),
    project_b: mapProject(raw.project_b),
    analysis: {
      distance_miles: f.distance_miles ?? null,
      geography_available: c.geography_available ?? false,
      schedule_overlap_months: f.schedule_overlap_months ?? null,
      temporal_precision: f.temporal_precision ?? null,
      year_difference: f.year_difference ?? null,
      same_active_year: f.same_active_year ?? null,
      geographic_score: c.geographic_score ?? null,
      temporal_score: c.temporal_score ?? null,
      text_similarity_score: c.text_similarity_score ?? null,
      infrastructure_similarity: c.infrastructure_similarity ?? null,
      coordination_score: raw.coordination_score,
      score_confidence: asConfidence(c.score_confidence),
      opportunity_rank: c.opportunity_rank ?? 0,
    },
    evidence: raw.reasons ?? [],
    // coordination_package.resources carries full per-resource evidence lists;
    // .shared_resources only has a single collapsed string, so resources is preferred.
    potential_shared_resources: (raw.coordination_package?.resources ?? []).flatMap((item) => {
      const mapped = mapResource(item);
      return mapped ? [mapped] : [];
    }),
    data_confidence: raw.data_confidence ?? {
      geography: null,
      temporal: null,
      similarity: null,
      overall_score: null,
    },
  };
}

function mapAnalyzeResponse(raw: RawAnalyzeResponse): AnalyzeResponse {
  const opportunities = (raw.opportunities ?? []).map(mapOpportunity);
  return {
    summary: {
      utilities: [raw.utility_a, raw.utility_b],
      projects_analyzed: raw.projects_analyzed,
      pairs_analyzed: raw.pairs_evaluated,
      eligible_opportunities: raw.opportunity_count,
      opportunities_returned: opportunities.length,
    },
    opportunities,
  };
}

export async function analyze(body: AnalyzeRequest): Promise<{ data: AnalyzeResponse; source: ResultSource }> {
  if (USE_MOCK) return { data: snapshot as AnalyzeResponse, source: "snapshot" };
  try {
    const res = await fetch(`${API_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Backend returned ${res.status} for /analyze`);
    const raw = await res.json();
    if (!Array.isArray(raw?.opportunities)) throw new Error("Unexpected /analyze response shape");
    const data = mapAnalyzeResponse(raw);
    return { data, source: "live" };
  } catch (e) {
    // Keep the demo running on the saved results, but loudly: the UI flags it and the console has the cause.
    console.error("GridSync: live analysis failed, showing saved results instead.", e);
    return { data: snapshot as AnalyzeResponse, source: "fallback" };
  }
}

function assistantError(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  if (status === 404) return "That pair is not in the current analysis.";
  return `The assistant could not answer (HTTP ${status}).`;
}

export async function askAssistant(body: AssistantQuery): Promise<AssistantResponse> {
  const payload: AssistantQuery = {
    query: body.query,
    messages: body.messages,
  };
  if (body.utility_a && body.utility_b) {
    payload.utility_a = body.utility_a;
    payload.utility_b = body.utility_b;
  }
  if (body.opportunity_id) payload.opportunity_id = body.opportunity_id;

  let res: Response;
  try {
    res = await fetch(`${API_URL}/assistant/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("Couldn't reach the analysis service. Check that the backend is running, then try again.");
  }

  const raw: unknown = await res.json().catch(() => null);
  if (!res.ok) throw new Error(assistantError(res.status, raw));
  if (!raw || typeof raw !== "object" || typeof (raw as { answer?: unknown }).answer !== "string") {
    throw new Error("The assistant response had no answer.");
  }
  const record = raw as {
    answer: string;
    note?: unknown;
    llm_used?: unknown;
    llm_configured?: unknown;
    assistant_mode?: unknown;
    sources?: unknown;
  };
  return {
    assistant_mode: "structured_retrieval",
    llm_used: record.llm_used === true,
    llm_configured: record.llm_configured === true,
    answer: record.answer,
    note: typeof record.note === "string" ? record.note : "",
    sources: parseSources(record.sources),
  };
}

function parseSources(value: unknown): AssistantSource[] {
  if (!Array.isArray(value)) return [];
  const sources: AssistantSource[] = [];
  for (const item of value) {
    if (
      item &&
      typeof item === "object" &&
      typeof (item as { document_title?: unknown }).document_title === "string" &&
      typeof (item as { page?: unknown }).page === "number"
    ) {
      sources.push({
        document_title: (item as { document_title: string }).document_title,
        page: (item as { page: number }).page,
      });
    }
  }
  return sources;
}

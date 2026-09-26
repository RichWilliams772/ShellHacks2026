import { API_URL, USE_MOCK } from "./config";
import type { AnalyzeRequest, AnalyzeResponse, Opportunity, Project, SharedResource } from "./types";
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

function voltageLabel(label: string | null, minKv: number | null, maxKv: number | null): string | null {
  if (label) return label;
  if (minKv == null || maxKv == null) return null;
  return minKv === maxKv ? `${minKv} kV` : `${minKv}-${maxKv} kV`;
}

function mapProject(raw: any): Project {
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
    date_precision: raw.date_precision ?? null,
    mid_lat: raw.latitude ?? null,
    mid_lon: raw.longitude ?? null,
    from_lat: raw.from_latitude ?? null,
    from_lon: raw.from_longitude ?? null,
    to_lat: raw.to_latitude ?? null,
    to_lon: raw.to_longitude ?? null,
    geometry_type: raw.geometry_type ?? null,
    location_confidence: raw.location_confidence ?? null,
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

function mapResource(raw: any): SharedResource {
  return {
    resource_id: raw.resource ?? raw.name,
    display_name: raw.label,
    potential: raw.potential ?? raw.strength,
    evidence: raw.evidence ?? (raw.reason ? [raw.reason] : []),
  };
}

function mapOpportunity(raw: any): Opportunity {
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
      score_confidence: c.score_confidence ?? null,
      opportunity_rank: c.opportunity_rank,
    },
    evidence: raw.reasons ?? [],
    // coordination_package.resources carries full per-resource evidence lists;
    // .shared_resources only has a single collapsed string, so resources is preferred.
    potential_shared_resources: (raw.coordination_package?.resources ?? []).map(mapResource),
    data_confidence: raw.data_confidence ?? {
      geography: null,
      temporal: null,
      similarity: null,
      overall_score: null,
    },
  };
}

function mapAnalyzeResponse(raw: any): AnalyzeResponse {
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

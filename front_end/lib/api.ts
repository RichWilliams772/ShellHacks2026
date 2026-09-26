import { API_URL, USE_MOCK, DEFAULT_UTILITY_A, DEFAULT_UTILITY_B } from "./config";
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  Confidence,
  GeometryPrecision,
  Opportunity,
  Project,
  SharedResource,
  Strength,
} from "./types";
import mockAnalyze from "./mock/analyze.json";
import mockProjects from "./mock/projects.json";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`Backend returned ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Normalization: converts the backend's response into lib/types.ts.
// Accepts both the PROJECT_SPEC §24 shape and the shape in the frontend brief
// (opportunity_id / analysis / shared_resources / name / construction_start),
// plus the data-analysis CSV column names (mid_lat / project_start / project_source …).
// It only renames and fills gaps with null — it never computes a score,
// distance, overlap, confidence, or resource.
// ---------------------------------------------------------------------------

type Raw = Record<string, unknown>;
const obj = (v: unknown): Raw => (v && typeof v === "object" ? (v as Raw) : {});
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const str = (v: unknown): string | null => (typeof v === "string" && v.trim() !== "" ? v : null);

function confidence(v: unknown): Confidence | null {
  const s = str(v)?.toUpperCase();
  return s === "HIGH" || s === "MEDIUM" || s === "LOW" || s === "UNKNOWN" ? s : null;
}

function precision(v: unknown): GeometryPrecision | null {
  const s = str(v)?.toLowerCase().replace(/[\s-]/g, "_");
  if (s === "route" || s === "exact" || s === "exact_route") return "route";
  if (s === "approximate_corridor" || s === "approximate") return "approximate_corridor";
  if (s === "endpoint_connection" || s === "endpoints" || s === "endpoint") return "endpoint_connection";
  return null;
}

function strength(v: unknown): Strength | null {
  const s = str(v)?.toUpperCase();
  return s === "HIGH" || s === "MEDIUM" || s === "LOW" ? s : null;
}

function normalizeProject(r: Raw): Project {
  return {
    id: String(r.id ?? r.project_id ?? "unknown"),
    utility: str(r.utility) ?? "Unknown utility",
    project_name: str(r.project_name) ?? str(r.name) ?? String(r.id ?? "Unnamed project"),
    project_type: str(r.project_type) ?? "unknown",
    description: str(r.description),
    // Duke has a min/max range; the data team's convention is to use the higher value (as TECO's voltage_kv does).
    voltage_kv: num(r.voltage_kv) ?? num(r.voltage_max_kv),
    // mid_lat/mid_lon = the data team's representative point (corridor midpoint or substation).
    latitude: num(r.latitude) ?? num(r.mid_lat),
    longitude: num(r.longitude) ?? num(r.mid_lon),
    geometry: r.geometry && obj(r.geometry).type ? (r.geometry as GeoJSON.Geometry) : null,
    geometry_precision: precision(r.geometry_precision ?? r.geometry_type),
    location_confidence: confidence(r.location_confidence),
    start_date: str(r.start_date) ?? str(r.construction_start) ?? str(r.project_start),
    end_date: str(r.end_date) ?? str(r.project_end) ?? str(r.in_service_date),
    status: str(r.status),
    capital_cost: num(r.capital_cost) ?? num(r.project_cost),
    customers_impacted: num(r.customers_impacted),
    source_name: str(r.source_name) ?? str(r.project_source) ?? "Source not provided",
    source_url: str(r.source_url) ?? "",
    source_document: str(r.source_document),
    source_page: (r.source_page as string | number | null) ?? null,
    retrieved_date: str(r.retrieved_date),
    data_type: r.data_type === "demo" ? "demo" : "public",
  };
}

function normalizeResources(o: Raw): SharedResource[] {
  const list = (obj(o.coordination_package).resources ?? o.shared_resources ?? []) as unknown[];
  if (!Array.isArray(list)) return [];
  return list
    .map((x) => {
      if (typeof x === "string") return { name: x, strength: null };
      const r = obj(x);
      const name = str(r.name) ?? str(r.resource);
      return name ? { name, strength: strength(r.strength ?? r.potential) } : null;
    })
    .filter((x): x is SharedResource => x !== null);
}

function normalizeOpportunity(o: Raw, i: number): Opportunity | null {
  if (!o.project_a || !o.project_b) return null;
  const a = normalizeProject(obj(o.project_a));
  const b = normalizeProject(obj(o.project_b));
  // Spec puts metrics in `features`; the brief puts them in `analysis`. Read both.
  const f = { ...obj(o.analysis), ...obj(o.features) };
  // A missing score is not a score of 0 — skip the row rather than rank it last.
  const score = num(o.coordination_score) ?? num(f.coordination_score);
  if (score == null) {
    console.warn(`GridSync: opportunity ${a.id} ↔ ${b.id} has no coordination_score; skipped.`);
    return null;
  }
  return {
    id: String(o.id ?? o.opportunity_id ?? `${a.id}__${b.id}__${i}`),
    project_a: a,
    project_b: b,
    features: {
      distance_miles: num(f.distance_miles),
      distance_km: num(f.distance_km),
      schedule_overlap_months: num(f.schedule_overlap_months),
      project_type_similarity: num(f.project_type_similarity),
      voltage_similarity: num(f.voltage_similarity),
      text_similarity: num(f.text_similarity),
      distance_similarity: num(f.distance_similarity),
      schedule_similarity: num(f.schedule_similarity),
      project_similarity: num(f.project_similarity),
      infrastructure_similarity: num(f.infrastructure_similarity),
    },
    coordination_score: score,
    reasons: Array.isArray(o.reasons) ? o.reasons.filter((r): r is string => typeof r === "string") : [],
    coordination_package: { resources: normalizeResources(o) },
  };
}

function normalize(raw: unknown): AnalyzeResponse {
  const r = obj(raw);
  const list = Array.isArray(raw) ? raw : Array.isArray(r.opportunities) ? r.opportunities : [];
  const opportunities = list
    .map((o, i) => normalizeOpportunity(obj(o), i))
    .filter((o): o is Opportunity => o !== null);
  const uniqueProjects = new Set(opportunities.flatMap((o) => [o.project_a.id, o.project_b.id]));
  return {
    projects_analyzed: num(r.projects_analyzed) ?? uniqueProjects.size,
    pairs_evaluated: num(r.pairs_evaluated),
    opportunities,
  };
}

// ---------------------------------------------------------------------------

export async function getUtilities(): Promise<string[]> {
  if (USE_MOCK) return [DEFAULT_UTILITY_A, DEFAULT_UTILITY_B];
  const data = await request<unknown>("/utilities");
  const list = Array.isArray(data) ? data : (obj(data).utilities as unknown[]) ?? [];
  return list.map((u) => (typeof u === "string" ? u : String(obj(u).name ?? ""))).filter(Boolean);
}

// All projects for the map, including ones with no match. Returns [] if the endpoint isn't ready.
export async function getProjects(): Promise<Project[]> {
  const raw = USE_MOCK
    ? (mockProjects as unknown[])
    : await request<unknown>("/projects").catch(() => [] as unknown[]);
  const list = Array.isArray(raw) ? raw : ((obj(raw).projects as unknown[]) ?? []);
  return list.map((p) => normalizeProject(obj(p)));
}

export async function analyze(body: AnalyzeRequest): Promise<AnalyzeResponse> {
  if (USE_MOCK) return normalize(mockAnalyze);
  const data = await request<unknown>("/analyze", { method: "POST", body: JSON.stringify(body) });
  return normalize(data);
}

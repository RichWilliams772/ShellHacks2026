// The shape every component reads. Mirrors PROJECT_SPEC.md §7 and §24.
// lib/api.ts converts whatever the backend actually returns into these types,
// so if the backend's field names change, only api.ts needs updating.

export type DataType = "public" | "demo";
export type Confidence = "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";

// How precise a project's line geometry is. Anything other than "route" is drawn
// dashed and labeled, so endpoint-only geography never looks like an exact line.
export type GeometryPrecision = "route" | "approximate_corridor" | "endpoint_connection";

export interface Project {
  id: string;
  utility: string;
  project_name: string;
  project_type: string;
  description: string | null;
  voltage_kv: number | null;
  latitude: number | null;
  longitude: number | null;
  geometry: GeoJSON.Geometry | null;
  geometry_precision?: GeometryPrecision | null;
  location_confidence?: Confidence | null;
  start_date: string | null; // ISO date or year, null when unknown
  end_date: string | null;
  status: string | null;
  capital_cost: number | null;
  customers_impacted: number | null;
  source_name: string;
  source_url: string;
  source_document?: string | null;
  source_page?: string | number | null;
  retrieved_date?: string | null;
  data_type: DataType;
}

export interface OpportunityFeatures {
  // Raw measurements
  distance_miles: number | null;
  distance_km?: number | null;
  schedule_overlap_months: number | null;
  // Similarities, 0–1
  project_type_similarity: number | null;
  voltage_similarity: number | null;
  text_similarity?: number | null;
  // Score components (spec §15 feature vector), 0–1. Shown as bars only when the backend sends them.
  distance_similarity?: number | null;
  schedule_similarity?: number | null;
  project_similarity?: number | null;
  infrastructure_similarity?: number | null;
}

export type Strength = "HIGH" | "MEDIUM" | "LOW";

export interface SharedResource {
  name: string; // e.g. "specialized_line_crews"
  strength: Strength | null; // null when the backend didn't classify it (e.g. plain-string resources)
}

export interface CoordinationPackage {
  resources: SharedResource[];
}

export interface Opportunity {
  id: string;
  project_a: Project;
  project_b: Project;
  features: OpportunityFeatures;
  coordination_score: number; // 0–100, computed by the backend only
  reasons: string[]; // plain sentences from the backend's structured analysis
  coordination_package: CoordinationPackage;
}

export interface AnalyzeRequest {
  utility_a: string;
  utility_b: string;
}

export interface AnalyzeResponse {
  projects_analyzed: number;
  pairs_evaluated: number | null;
  opportunities: Opportunity[];
}

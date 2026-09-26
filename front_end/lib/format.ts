import { UTILITY_COLORS, FALLBACK_COLORS } from "./config";
import type { Analysis, Project } from "./types";

// Null means "unknown", never zero (spec §7). Every formatter returns "Not available" for null.
export const NA = "Not available";

export function fmtMiles(v: number | null | undefined) {
  return v == null ? NA : `${v.toFixed(1)} mi`;
}

export function fmtDate(v: string | null | undefined) {
  if (!v) return NA;
  const d = new Date(`${v.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

// Month-precision projects show their dates; year-only projects say so rather than inventing a date.
export function fmtSchedule(p: Project) {
  if (p.start || p.end) return `${fmtDate(p.start)} – ${fmtDate(p.end)}`;
  if (p.in_service_year != null) return `In service ${p.in_service_year} (year only)`;
  return NA;
}

// Schedule relationship between the two projects, as reported by the temporal engine.
export function fmtScheduleGap(a: Analysis) {
  if (a.schedule_overlap_months != null)
    return a.schedule_overlap_months > 0 ? `${a.schedule_overlap_months}-month overlap` : "No overlap";
  if (a.same_active_year) return "Same active year";
  if (a.year_difference != null) return `~${a.year_difference} yr apart`;
  return NA;
}

// Years a project is active in, for the year filter.
export function projectYears(p: Project): number[] {
  const s = p.start ? Number(p.start.slice(0, 4)) : null;
  const e = p.end ? Number(p.end.slice(0, 4)) : s;
  if (s != null && e != null) return Array.from({ length: e - s + 1 }, (_, i) => s + i);
  return p.in_service_year != null ? [p.in_service_year] : [];
}

// "transmission_upgrade" -> "Transmission upgrade"
export function humanize(v: string | null | undefined) {
  if (!v) return NA;
  const s = v.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function shortUtility(name: string) {
  if (name === "Duke Energy Florida") return "Duke";
  if (name === "Tampa Electric") return "TECO";
  return name;
}

const assigned = new Map<string, string>();
export function utilityColor(name: string) {
  if (UTILITY_COLORS[name]) return UTILITY_COLORS[name];
  if (!assigned.has(name)) {
    assigned.set(name, FALLBACK_COLORS[assigned.size % FALLBACK_COLORS.length]);
  }
  return assigned.get(name)!;
}

// Second visual cue besides color: Duke = circle, TECO = diamond.
export type MarkerShape = "circle" | "diamond" | "square";
export function utilityShape(name: string): MarkerShape {
  if (name === "Tampa Electric") return "diamond";
  if (name === "Duke Energy Florida") return "circle";
  return "square";
}

export const CONFIDENCE_HELP = "Confidence represents the quality of available geographic project data.";
export const SCORE_HELP =
  "Composite indicator based on geographic proximity, schedule overlap, project similarity, and available infrastructure characteristics. A GridSync prototype measure, not an industry-standard utility metric.";

export function geometryLabel(g: Project["geometry_type"]) {
  if (g === "approximate_corridor") return "Approximate corridor (straight line between endpoints, not the route)";
  if (g === "point") return "Single substation";
  return NA;
}

import { UTILITY_COLORS, FALLBACK_COLORS } from "./config";

// Null means "unknown", never zero (spec §7). Every formatter returns "Not available" for null.
export const NA = "Not available";

export function fmtMiles(v: number | null | undefined) {
  return v == null ? NA : `${v.toFixed(1)} mi`;
}

export function fmtMonths(v: number | null | undefined) {
  if (v == null) return NA;
  if (v === 0) return "No overlap";
  return `${v} month${v === 1 ? "" : "s"}`;
}

export function fmtPct(v: number | null | undefined) {
  return v == null ? NA : `${Math.round(v * 100)}%`;
}

export function fmtKv(v: number | null | undefined) {
  return v == null ? NA : `${v} kV`;
}

export function fmtMoney(v: number | null | undefined) {
  if (v == null) return NA;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(v);
}

export function fmtInt(v: number | null | undefined) {
  return v == null ? NA : v.toLocaleString("en-US");
}

export function fmtDate(v: string | null | undefined) {
  if (!v) return NA;
  if (/^\d{4}$/.test(v)) return v; // year-only dates stay year-only
  const iso = /^\d{4}-\d{2}$/.test(v) ? `${v}-01` : v; // "2026-06" -> Jun 2026
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

export function fmtPeriod(start: string | null, end: string | null) {
  if (!start && !end) return NA;
  return `${fmtDate(start)} – ${fmtDate(end)}`;
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

export function years(start: string | null, end: string | null): number[] {
  const s = start ? Number(start.slice(0, 4)) : NaN;
  const e = end ? Number(end.slice(0, 4)) : s;
  if (Number.isNaN(s)) return [];
  const out: number[] = [];
  for (let y = s; y <= (Number.isNaN(e) ? s : e); y++) out.push(y);
  return out;
}

// Second visual cue besides color (brief §6): Duke = circle, TECO = diamond.
export type MarkerShape = "circle" | "diamond" | "square";
export function utilityShape(name: string): MarkerShape {
  if (name === "Tampa Electric") return "diamond";
  if (name === "Duke Energy Florida") return "circle";
  return "square";
}

export const CONFIDENCE_HELP = "Confidence represents the quality of available geographic project data.";
export const SCORE_HELP =
  "Composite indicator based on geographic proximity, schedule overlap, project similarity, and available infrastructure characteristics. A GridSync prototype measure, not an industry-standard utility metric.";

export function precisionLabel(p: string | null | undefined) {
  if (p === "route") return "Mapped route";
  if (p === "endpoint_connection") return "Endpoint connection (not an exact route)";
  return "Approximate project corridor (not an exact route)";
}

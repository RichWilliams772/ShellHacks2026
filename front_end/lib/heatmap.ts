// Turns existing opportunities into heat points. Computes nothing new: every point is a
// project's own mid_lat/mid_lon (the same point the normal map already draws a marker at),
// weighted by the pipeline's own coordination_score. No geocoding, no new geometry.
//
// Each opportunity contributes its weight at BOTH projects' locations, not at a midpoint
// between them. Duke and TECO projects can sit 50+ miles apart; a midpoint between two real
// sites can land in open country with no infrastructure at all, implying concentration where
// none exists. Anchoring every heat pixel to an existing, already-displayed project location
// keeps the heatmap honest about what it represents.
import type { Opportunity } from "./types";

// [lat, lon, weight] — the shape leaflet.heat expects. Weight is coordination_score / 100.
export type HeatPoint = [number, number, number];

export function buildHeatPoints(opportunities: Opportunity[]): HeatPoint[] {
  const points: HeatPoint[] = [];
  for (const o of opportunities) {
    const weight = o.analysis.coordination_score / 100;
    for (const p of [o.project_a, o.project_b]) {
      if (p.mid_lat != null && p.mid_lon != null) points.push([p.mid_lat, p.mid_lon, weight]);
    }
  }
  return points;
}

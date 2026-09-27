"use client";

// Leaflet touches `window`, so this file is only loaded client-side via MapPanel (dynamic, ssr:false).
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo } from "react";
import L from "leaflet";
import { MapContainer, TileLayer, Marker, Polyline, Tooltip, useMap } from "react-leaflet";
import type { Opportunity, Project } from "@/lib/types";
import { MAP_CENTER, MAP_ZOOM, REDLINE } from "@/lib/config";
import { fmtMiles, shortUtility, utilityColor, utilityShape } from "@/lib/format";
import HeatmapLayer from "./HeatmapLayer";
import type { HeatPoint } from "@/lib/heatmap";

export type MapMode = "map" | "heatmap";

interface Props {
  projects: Project[];
  selected: Opportunity | null;
  onSelectProject?: (projectId: string) => void;
  // Both default to the existing single-map behavior, so no caller has to change.
  mode?: MapMode;
  heatPoints?: HeatPoint[];
}

type LL = [number, number];

const point = (p: Project): LL | null => (p.mid_lat != null && p.mid_lon != null ? [p.mid_lat, p.mid_lon] : null);

const corridor = (p: Project): LL[] | null =>
  p.geometry_type === "approximate_corridor" && p.from_lat != null && p.from_lon != null && p.to_lat != null && p.to_lon != null
    ? [
        [p.from_lat, p.from_lon],
        [p.to_lat, p.to_lon],
      ]
    : null;

const reducedMotion = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Where to draw the dimension line. The pipeline measures distance between the nearest known
// endpoints, so the line connects those; this only picks drawing positions, it never changes the number.
function dimensionEnds(a: Project, b: Project): [LL, LL] | null {
  const ends = (p: Project) => corridor(p) ?? (point(p) ? [point(p)!] : []);
  let best: [LL, LL] | null = null;
  let bestD = Infinity;
  for (const pa of ends(a))
    for (const pb of ends(b)) {
      const d = (pa[0] - pb[0]) ** 2 + ((pa[1] - pb[1]) * Math.cos((pa[0] * Math.PI) / 180)) ** 2;
      if (d < bestD) [bestD, best] = [d, [pa, pb]];
    }
  return best;
}

// Short perpendicular ticks at each end, like a dimension on an engineering drawing.
function ticks([p, q]: [LL, LL]): LL[][] {
  const dy = q[0] - p[0];
  const dx = q[1] - p[1];
  const len = Math.hypot(dx, dy) || 1;
  const s = Math.max(len * 0.035, 0.008);
  const [ny, nx] = [(dx / len) * s, (-dy / len) * s];
  return [p, q].map((e) => [
    [e[0] + ny, e[1] + nx],
    [e[0] - ny, e[1] - nx],
  ]);
}

// Deterministic 0-1.8s stagger from the project id, so 20-50 markers don't all pulse in
// lockstep (which reads as a synchronized flash, not ambient activity).
function pulseDelay(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return (h % 900) / 500;
}

function markerIcon(p: Project, selected: boolean, dimmed: boolean) {
  const size = selected ? 20 : 13;
  const shape = utilityShape(p.utility);
  const color = utilityColor(p.utility);
  const radius = shape === "circle" ? "9999px" : "1px";
  const rotate = shape === "diamond" ? "rotate(45deg) scale(0.85)" : "none";
  const border = selected ? `3px solid ${REDLINE}` : "2px solid #f7f8f5";
  // Room for the pulse ring to expand to ~2.6x the dot without clipping.
  const box = Math.ceil(size * 2.6);
  const c = box / 2;
  const half = size / 2;
  const html = `<div style="position:relative;width:${box}px;height:${box}px;opacity:${dimmed ? 0.35 : 1}">
    <span class="marker-pulse" style="position:absolute;left:${c - half}px;top:${c - half}px;width:${size}px;height:${size}px;background:${color};border-radius:9999px;animation-delay:${pulseDelay(p.id)}s${dimmed ? ";animation-play-state:paused" : ""}"></span>
    <div style="position:absolute;left:${c - half}px;top:${c - half}px;width:${size}px;height:${size}px;background:${color};border:${border};border-radius:${radius};transform:${rotate};box-shadow:0 1px 3px rgba(27,34,48,0.5)"></div>
  </div>`;
  return L.divIcon({ html, className: "", iconSize: [box, box], iconAnchor: [c, c] });
}

// After an analysis loads, frame every located project (Duke spans most of the state, not just Tampa Bay).
function FitToProjects({ projects }: { projects: Project[] }) {
  const map = useMap();
  useEffect(() => {
    const pts = projects.map(point).filter((x): x is LL => x !== null);
    if (pts.length > 0) map.fitBounds(pts, { padding: [40, 40], maxZoom: 10, animate: !reducedMotion() });
  }, [projects, map]);
  return null;
}

function FitToSelection({ selected }: { selected: Opportunity | null }) {
  const map = useMap();
  useEffect(() => {
    if (!selected) return;
    const pts = [selected.project_a, selected.project_b].flatMap((p) => corridor(p) ?? (point(p) ? [point(p)!] : []));
    if (pts.length === 0) return;
    if (reducedMotion()) map.fitBounds(pts, { padding: [90, 90], maxZoom: 11, animate: false });
    else map.flyToBounds(pts, { padding: [90, 90], maxZoom: 11, duration: 0.8 });
  }, [selected, map]);
  return null;
}

export default function ProjectMap({ projects, selected, onSelectProject, mode = "map", heatPoints = [] }: Props) {
  const selA = selected?.project_a.id;
  const selB = selected?.project_b.id;
  const isSel = (id: string) => id === selA || id === selB;
  const dim = selected != null;

  // Draw selected projects last so they sit on top.
  const ordered = useMemo(
    () => [...projects].sort((x, y) => Number(x.id === selA || x.id === selB) - Number(y.id === selA || y.id === selB)),
    [projects, selA, selB],
  );

  const dimension = selected ? dimensionEnds(selected.project_a, selected.project_b) : null;

  return (
    <MapContainer center={MAP_CENTER} zoom={MAP_ZOOM} scrollWheelZoom={false} className="h-full w-full">
      {/* CARTO's keyless basemaps were retired (now gate behind an API key), so this stays on
          OSM's own tiles - the CSS filter below is what keeps the color muted, not the source. */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToProjects projects={projects} />
      {mode === "map" && <FitToSelection selected={selected} />}

      {/* Portfolio-level view: density + score of existing opportunities, nothing new computed.
          Replaces the individual markers below rather than overlaying them - the two modes
          answer different questions (discovery vs. inspection), not the same one twice. */}
      {mode === "heatmap" && <HeatmapLayer points={heatPoints} />}

      {/* Approximate corridors: a straight dashed line between endpoints, never presented as the route. */}
      {mode === "map" && ordered.map((p) => {
        const line = corridor(p);
        if (!line) return null;
        const sel = isSel(p.id);
        return (
          <Polyline
            key={`corridor-${p.id}-${sel}`}
            positions={line}
            pathOptions={{ color: utilityColor(p.utility), weight: sel ? 4 : 2.5, opacity: dim && !sel ? 0.25 : 0.9, dashArray: "6 6" }}
          >
            <Tooltip sticky>Approximate corridor, not the physical route</Tooltip>
          </Polyline>
        );
      })}

      {mode === "map" && ordered.map((p) => {
        const pos = point(p);
        if (!pos) return null;
        const sel = isSel(p.id);
        return (
          <Marker
            key={p.id}
            position={pos}
            icon={markerIcon(p, sel, dim && !sel)}
            zIndexOffset={sel ? 1000 : 0}
            eventHandlers={{ click: () => onSelectProject?.(p.id) }}
          >
            {/* Name only on hover; clicking opens the project's best pair in the side panel. */}
            <Tooltip direction="top" offset={[0, -8]}>
              {shortUtility(p.utility)}: {p.name}
            </Tooltip>
          </Marker>
        );
      })}

      {mode === "map" && selected && dimension && (
        <>
          <Polyline key={`dim-${selected.opportunity_id}`} positions={dimension} pathOptions={{ color: REDLINE, weight: 2.5 }}>
            <Tooltip permanent direction="center" className="dimension-label">
              {fmtMiles(selected.analysis.distance_miles)}
            </Tooltip>
          </Polyline>
          {ticks(dimension).map((t, i) => (
            <Polyline key={`tick-${selected.opportunity_id}-${i}`} positions={t} pathOptions={{ color: REDLINE, weight: 2.5 }} />
          ))}
        </>
      )}
    </MapContainer>
  );
}

"use client";

// Leaflet touches `window`, so this file is only loaded client-side via MapPanel (dynamic, ssr:false).
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo } from "react";
import L from "leaflet";
import { MapContainer, TileLayer, Marker, Polyline, Popup, Tooltip, GeoJSON, useMap } from "react-leaflet";
import type { LatLngExpression, LatLngBoundsExpression } from "leaflet";
import type { Opportunity, Project } from "@/lib/types";
import { MAP_CENTER, MAP_ZOOM } from "@/lib/config";
import {
  fmtKv,
  fmtMiles,
  fmtPeriod,
  humanize,
  precisionLabel,
  shortUtility,
  utilityColor,
  utilityShape,
  NA,
} from "@/lib/format";

interface Props {
  projects: Project[];
  selected: Opportunity | null;
  onSelectProject?: (projectId: string) => void;
}

const hasPoint = (p: Project) => p.latitude != null && p.longitude != null;
const isLine = (g: GeoJSON.Geometry | null) => g?.type === "LineString" || g?.type === "MultiLineString";

// HTML marker so each utility gets its own shape (circle / diamond / square), not just its own color.
function markerIcon(p: Project, selected: boolean, dimmed: boolean) {
  const size = selected ? 22 : 14;
  const color = utilityColor(p.utility);
  const shape = utilityShape(p.utility);
  const radius = shape === "circle" ? "9999px" : "2px";
  const rotate = shape === "diamond" ? "rotate(45deg) scale(0.85)" : "none";
  const border = selected ? "3px solid #0f172a" : "2px solid #ffffff";
  const html = `<div style="width:${size}px;height:${size}px;background:${color};border:${border};border-radius:${radius};transform:${rotate};opacity:${dimmed ? 0.35 : 1};box-shadow:0 1px 3px rgba(0,0,0,.35)"></div>`;
  return L.divIcon({ html, className: "", iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
}

// After an analysis loads, frame every located project (Duke spans most of the state, not just Tampa Bay).
function FitToProjects({ projects }: { projects: Project[] }) {
  const map = useMap();
  useEffect(() => {
    const pts = projects.filter(hasPoint).map((p): [number, number] => [p.latitude!, p.longitude!]);
    if (pts.length > 0) map.fitBounds(pts, { padding: [40, 40], maxZoom: 10 });
  }, [projects, map]);
  return null;
}

function FitToSelection({ selected }: { selected: Opportunity | null }) {
  const map = useMap();
  useEffect(() => {
    if (!selected) return;
    const pts = [selected.project_a, selected.project_b].filter(hasPoint);
    if (pts.length === 0) return;
    const bounds = pts.map((p) => [p.latitude!, p.longitude!]) as LatLngBoundsExpression;
    map.flyToBounds(bounds, { padding: [80, 80], maxZoom: 11, duration: 0.6 });
  }, [selected, map]);
  return null;
}

function ProjectPopup({ p }: { p: Project }) {
  return (
    <div className="min-w-[200px] text-xs leading-5">
      <p className="text-sm font-semibold text-slate-900">{p.project_name}</p>
      <p className="text-slate-600">{p.utility}</p>
      <p className="mt-1">
        <span className="text-slate-500">Type:</span> {humanize(p.project_type)}
      </p>
      <p>
        <span className="text-slate-500">Voltage:</span> {fmtKv(p.voltage_kv)}
      </p>
      <p>
        <span className="text-slate-500">Status:</span> {humanize(p.status)}
      </p>
      <p>
        <span className="text-slate-500">Schedule:</span> {fmtPeriod(p.start_date, p.end_date)}
      </p>
      <p>
        <span className="text-slate-500">Location confidence:</span> {p.location_confidence ?? NA}
      </p>
      {p.data_type === "demo" && <p className="mt-1 font-semibold text-amber-700">Demo record</p>}
    </div>
  );
}

export default function ProjectMap({ projects, selected, onSelectProject }: Props) {
  const selA = selected?.project_a.id;
  const selB = selected?.project_b.id;
  const isSel = (id: string) => id === selA || id === selB;
  const dimOthers = selected != null;

  const a = selected?.project_a;
  const b = selected?.project_b;
  const link: LatLngExpression[] | null =
    a && b && hasPoint(a) && hasPoint(b)
      ? [
          [a.latitude!, a.longitude!],
          [b.latitude!, b.longitude!],
        ]
      : null;

  // Draw selected projects last so they sit on top.
  const ordered = useMemo(
    () => [...projects].sort((x, y) => Number(x.id === selA || x.id === selB) - Number(y.id === selA || y.id === selB)),
    [projects, selA, selB],
  );

  return (
    <MapContainer center={MAP_CENTER} zoom={MAP_ZOOM} scrollWheelZoom className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToProjects projects={projects} />
      <FitToSelection selected={selected} />

      {/* Line geometry. Only "route" is drawn solid; approximate/endpoint geometry is dashed and labeled. */}
      {ordered
        .filter((p) => isLine(p.geometry))
        .map((p) => {
          const exact = p.geometry_precision === "route";
          return (
            <GeoJSON
              key={`route-${p.id}-${isSel(p.id)}`}
              data={p.geometry as GeoJSON.Geometry}
              style={{
                color: utilityColor(p.utility),
                weight: isSel(p.id) ? 5 : 3,
                opacity: dimOthers && !isSel(p.id) ? 0.25 : 0.8,
                dashArray: exact ? undefined : "2 8",
                lineCap: "round",
              }}
            >
              <Tooltip sticky>
                <span className="text-xs">
                  {shortUtility(p.utility)} · {precisionLabel(p.geometry_precision)}
                </span>
              </Tooltip>
            </GeoJSON>
          );
        })}

      {ordered.filter(hasPoint).map((p) => {
        const sel = isSel(p.id);
        return (
          <Marker
            key={p.id}
            position={[p.latitude!, p.longitude!]}
            icon={markerIcon(p, sel, dimOthers && !sel)}
            zIndexOffset={sel ? 1000 : 0}
            eventHandlers={{ click: () => onSelectProject?.(p.id) }}
          >
            <Popup>
              <ProjectPopup p={p} />
            </Popup>
          </Marker>
        );
      })}

      {link && (
        <Polyline positions={link} pathOptions={{ color: "#0f172a", weight: 2, dashArray: "6 6" }}>
          <Tooltip permanent direction="center" className="!rounded-md !border-slate-900 !font-semibold">
            {fmtMiles(selected!.features.distance_miles)} apart
          </Tooltip>
        </Polyline>
      )}
    </MapContainer>
  );
}

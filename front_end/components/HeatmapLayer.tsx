"use client";

// Mounts the existing map library's own heat layer onto the same Leaflet instance the normal
// map already uses. No new mapping framework, no custom heat renderer.
import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";
import type { HeatPoint } from "@/lib/heatmap";
// lib/leaflet-heat.d.ts augments the "leaflet" module with L.heatLayer's type - TypeScript
// picks up ambient .d.ts files automatically (tsconfig's `include` covers **/*.ts), so it
// needs no import here. An earlier version of this file imported it as a runtime module,
// which crashed the dev server ("Unexpected identifier 'module'") - a .d.ts has no runtime
// body to execute.

interface Props {
  points: HeatPoint[];
}

export default function HeatmapLayer({ points }: Props) {
  const map = useMap();

  // Block body, explicit cleanup function: adding a layer and forgetting to remove it on
  // dependency change or unmount would leak a duplicate layer onto the map every re-render.
  useEffect(() => {
    if (points.length === 0) return;
    // max is calibrated below the true 0-1 weight ceiling so a real concentration of
    // high-scoring points reaches the gradient's warm end at this dataset's size - a display
    // calibration only, not a change to any weight value itself (still coordination_score/100).
    const layer = L.heatLayer(points, { radius: 30, blur: 20, max: 0.55, minOpacity: 0.2 }).addTo(map);
    return () => {
      map.removeLayer(layer);
    };
  }, [points, map]);

  return null;
}

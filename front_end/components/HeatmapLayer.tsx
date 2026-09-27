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
    // leaflet.heat scales every point's weight by f = 1 / 2^clamp(maxZoom - currentZoom, 0, 12)
    // before drawing (its own zoom-compensation step) - left at the library's maxZoom default
    // (~18, far above this app's actual operating range around zoom 7-11), f collapses to
    // ~0.0005 at the default view. At that scale every real score (0.06-0.63) draws far below
    // minOpacity regardless of value, so the display showed point count, not score - confirmed
    // by simulating the library's exact arithmetic against the real weight distribution.
    // Anchoring maxZoom to 11 - the same ceiling FitToProjects/FitToSelection already use
    // elsewhere in this file's sibling ProjectMap.tsx, not a new constant - and calibrating max
    // to the resulting single-point range (~0.004-0.04 at zoom 7) keeps the true top score close
    // to full intensity while leaving headroom for genuine clusters to read hotter still.
    // The site's own palette, not leaflet.heat's default rainbow - keeps the heatmap's "hottest"
    // color the same redline used everywhere else for the one thing on the map that matters most.
    const gradient = { 0.2: "#c9cec6", 0.45: "#5b6472", 0.7: "#1b2230", 1: "#c8352b" };
    const layer = L.heatLayer(points, { radius: 30, blur: 20, max: 0.05, minOpacity: 0.05, maxZoom: 11, gradient }).addTo(map);
    // leaflet.heat redraws on moveend, not on the resize invalidateSize emits.
    const redraw = () => {
      map.fire("moveend");
    };
    map.on("resize", redraw);
    return () => {
      map.off("resize", redraw);
      map.removeLayer(layer);
    };
  }, [points, map]);

  return null;
}

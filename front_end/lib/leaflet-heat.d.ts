// leaflet.heat ships no types of its own. This declares only what HeatmapLayer.tsx uses.
import "leaflet";

declare module "leaflet" {
  interface HeatLayerOptions {
    radius?: number;
    blur?: number;
    max?: number;
    minOpacity?: number;
    maxZoom?: number;
    gradient?: Record<number, string>;
  }
  function heatLayer(
    points: Array<[number, number, number]>,
    options?: HeatLayerOptions,
  ): L.Layer;
}

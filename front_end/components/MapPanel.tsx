"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { Opportunity, Project } from "@/lib/types";
import { buildHeatPoints } from "@/lib/heatmap";
import { UTILITY_A, UTILITY_B } from "@/lib/config";
import { shortUtility, utilityColor, utilityShape } from "@/lib/format";
import UtilityMarker from "./UtilityMarker";
import ChatWidget from "./ChatWidget";
import type { MapMode } from "./ProjectMap";

const ProjectMap = dynamic(() => import("./ProjectMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-paper" />,
});

interface Props {
  projects: Project[];
  selected: Opportunity | null;
  onSelectProject?: (projectId: string) => void;
  // The already-filtered list Dashboard computes for the side list - reused as-is, not
  // refiltered here, so the heatmap never invents its own filtering rules.
  opportunities: Opportunity[];
}

export default function MapPanel({ projects, selected, onSelectProject, opportunities }: Props) {
  const [mode, setMode] = useState<MapMode>("map");
  const heatPoints = useMemo(() => buildHeatPoints(opportunities), [opportunities]);

  return (
    <section className="relative h-[60vh] min-h-[420px] lg:h-full">
      <ProjectMap projects={projects} selected={selected} onSelectProject={onSelectProject} mode={mode} heatPoints={heatPoints} />

      <div
        className="absolute top-3 right-3 z-[1000] flex overflow-hidden rounded-full border border-ink bg-sheet text-sm shadow-[0_4px_14px_-6px_rgba(27,34,48,0.35)]"
        role="group"
        aria-label="Map view"
      >
        {(["map", "heatmap"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            aria-pressed={mode === m}
            className={`px-4 py-1.5 font-semibold ${m === "map" ? "border-r border-ink" : ""} ${
              mode === m ? "bg-ink text-paper" : "hover:bg-rule"
            }`}
          >
            {m === "map" ? "Map" : "Coordination Heatmap"}
          </button>
        ))}
      </div>

      {mode === "map" && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] space-y-1 rounded-lg border border-ink bg-sheet/95 px-3 py-2 text-sm shadow-[0_4px_14px_-6px_rgba(27,34,48,0.3)]">
          {[UTILITY_A, UTILITY_B].map((u) => (
            <p key={u} className="flex items-center gap-2">
              <UtilityMarker shape={utilityShape(u)} color={utilityColor(u)} />
              {shortUtility(u)} project
            </p>
          ))}
          <p className="flex items-center gap-2">
            <span className="w-5 border-t-2 border-dashed border-graphite" /> Approximate corridor
          </p>
          {selected && (
            <p className="flex items-center gap-2">
              <span className="w-5 border-t-2 border-redline" /> Distance between the pair
            </p>
          )}
        </div>
      )}

      {mode === "heatmap" && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] max-w-[280px] space-y-1 rounded-lg border border-ink bg-sheet/95 px-3 py-2 text-sm shadow-[0_4px_14px_-6px_rgba(27,34,48,0.3)]">
          <p className="font-display font-semibold tracking-wide uppercase">Coordination opportunity density</p>
          <div className="flex items-center gap-2">
            <span className="text-xs text-graphite">Lower</span>
            <span
              className="h-2 flex-1 rounded-full"
              style={{ background: "linear-gradient(to right, #c9cec6 0%, #5b6472 35%, #1b2230 70%, #c8352b 100%)" }}
            />
            <span className="text-xs text-graphite">Higher</span>
          </div>
          <p className="text-xs text-graphite">
            Reflects the concentration and Coordination Scores of GridSync opportunities nearby - not grid load,
            reliability, or congestion.
          </p>
        </div>
      )}

      {projects.length === 0 && (
        <p className="pointer-events-none absolute inset-x-0 top-6 z-[1000] mx-auto w-fit max-w-[90%] rounded-lg border border-ink bg-sheet px-4 py-2 text-center shadow-[0_4px_14px_-6px_rgba(27,34,48,0.3)]">
          Run the analysis to place both utilities&apos; planned projects on the map.
        </p>
      )}

      {mode === "heatmap" && projects.length > 0 && heatPoints.length === 0 && (
        <p className="pointer-events-none absolute inset-x-0 top-6 z-[1000] mx-auto w-fit max-w-[90%] rounded-lg border border-ink bg-sheet px-4 py-2 text-center shadow-[0_4px_14px_-6px_rgba(27,34,48,0.3)]">
          No coordination opportunities with sufficient location data are available for this view.
        </p>
      )}

      {projects.length > 0 && <ChatWidget opportunity={selected} />}
    </section>
  );
}

"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { Opportunity, Project } from "@/lib/types";
import { buildHeatPoints } from "@/lib/heatmap";
import { UTILITY_A, UTILITY_B } from "@/lib/config";
import { shortUtility, utilityColor, utilityShape } from "@/lib/format";
import UtilityMarker from "./UtilityMarker";
import type { MapMode } from "./ProjectMap";

const ProjectMap = dynamic(() => import("./ProjectMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-[#d5dde6]" />,
});

interface Props {
  projects: Project[];
  selected: Opportunity | null;
  onSelectProject?: (projectId: string) => void;
  // The already-filtered list Dashboard computes for the side list - reused as-is, not
  // refiltered here, so the heatmap never invents its own filtering rules.
  opportunities: Opportunity[];
}

function MapKey({ selected }: { selected: boolean }) {
  return (
    <>
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
    </>
  );
}

function HeatKey() {
  return (
    <>
      <p className="font-display font-semibold tracking-wide uppercase">Coordination opportunity density</p>
      <div className="flex items-center gap-2">
        <span className="text-xs text-graphite">Lower</span>
        <span className="h-2 flex-1 rounded-full bg-gradient-to-r from-blue-500 via-yellow-300 to-red-500" />
        <span className="text-xs text-graphite">Higher</span>
      </div>
      <p className="text-xs text-graphite">
        Reflects the concentration and Coordination Scores of GridSync opportunities nearby - not grid load, reliability,
        or congestion.
      </p>
    </>
  );
}

export default function MapPanel({ projects, selected, onSelectProject, opportunities }: Props) {
  const [mode, setMode] = useState<MapMode>("map");
  const heatPoints = useMemo(() => buildHeatPoints(opportunities), [opportunities]);

  return (
    <>
    <section className="gs-map relative h-60 w-full min-w-0 overflow-hidden sm:h-[60vh] sm:min-h-[420px] lg:h-full lg:min-h-0 lg:min-w-[360px] lg:flex-1 lg:basis-0">
      <ProjectMap projects={projects} selected={selected} onSelectProject={onSelectProject} mode={mode} heatPoints={heatPoints} />

      <div
        className="absolute top-2 right-2 left-[4.25rem] z-[1000] flex overflow-hidden rounded-full border border-rule bg-sheet text-sm sm:top-3 sm:right-3 sm:left-auto sm:max-w-[calc(100%-4.75rem)] sm:flex-wrap sm:justify-end"
        role="group"
        aria-label="Map view"
      >
        {(["map", "heatmap"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            aria-pressed={mode === m}
            aria-label={m === "map" ? "Map" : "Coordination Heatmap"}
            className={`min-h-11 flex-1 px-3 py-2 text-center font-semibold sm:min-h-0 sm:flex-none sm:py-1.5 ${m === "map" ? "border-r border-rule" : ""} ${
              mode === m ? "bg-cyan text-paper" : "text-ink hover:bg-white/5"
            }`}
          >
            {m === "map" ? (
              "Map"
            ) : (
              <>
                <span className="sm:hidden">Heatmap</span>
                <span className="hidden sm:inline">Coordination Heatmap</span>
              </>
            )}
          </button>
        ))}
      </div>

      {mode === "map" && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] hidden max-w-[min(16rem,calc(100%-13rem))] space-y-1 rounded-md border border-rule bg-sheet/95 px-3 py-2 text-sm break-words sm:block">
          <MapKey selected={selected != null} />
        </div>
      )}

      {mode === "heatmap" && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] hidden max-w-[min(16rem,calc(100%-13rem))] space-y-1 rounded-md border border-rule bg-sheet/95 px-3 py-2 text-sm break-words sm:block">
          <HeatKey />
        </div>
      )}

      {projects.length === 0 && (
        <p className="pointer-events-none absolute inset-x-3 top-[4.75rem] z-[1000] mx-auto w-fit max-w-[calc(100%-1.5rem)] rounded-md border border-rule bg-sheet px-4 py-2 text-center sm:top-16">
          Run the analysis to place both utilities&apos; planned projects on the map.
        </p>
      )}

      {mode === "heatmap" && projects.length > 0 && heatPoints.length === 0 && (
        <p className="pointer-events-none absolute inset-x-3 top-[4.75rem] z-[1000] mx-auto w-fit max-w-[calc(100%-1.5rem)] rounded-md border border-rule bg-sheet px-4 py-2 text-center break-words sm:top-16">
          No coordination opportunities with sufficient location data are available for this view.
        </p>
      )}
    </section>
    {mode === "map" && (
      <div className="space-y-1 border-b border-rule bg-sheet px-4 py-2 text-xs break-words sm:hidden">
        <MapKey selected={selected != null} />
      </div>
    )}
    {mode === "heatmap" && (
      <div className="space-y-1 border-b border-rule bg-sheet px-4 py-3 text-sm break-words sm:hidden">
        <HeatKey />
      </div>
    )}
    </>
  );
}

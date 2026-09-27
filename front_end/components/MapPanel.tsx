"use client";

import dynamic from "next/dynamic";
import type { Opportunity, Project } from "@/lib/types";
import { UTILITY_A, UTILITY_B } from "@/lib/config";
import { shortUtility, utilityColor, utilityShape } from "@/lib/format";
import UtilityMarker from "./UtilityMarker";

const ProjectMap = dynamic(() => import("./ProjectMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-paper" />,
});

interface Props {
  projects: Project[];
  selected: Opportunity | null;
  onSelectProject?: (projectId: string) => void;
}

export default function MapPanel({ projects, selected, onSelectProject }: Props) {
  return (
    <section className="relative h-[60vh] min-h-[420px] lg:h-full">
      <ProjectMap projects={projects} selected={selected} onSelectProject={onSelectProject} />

      <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] space-y-1 border border-ink bg-sheet/95 px-3 py-2 text-sm">
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

      {projects.length === 0 && (
        <p className="pointer-events-none absolute inset-x-0 top-6 z-[1000] mx-auto w-fit max-w-[90%] border border-ink bg-sheet px-4 py-2 text-center">
          Run the analysis to place both utilities&apos; planned projects on the map.
        </p>
      )}
    </section>
  );
}

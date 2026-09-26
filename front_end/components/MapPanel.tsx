"use client";

import dynamic from "next/dynamic";
import type { Opportunity, Project } from "@/lib/types";
import { shortUtility, utilityColor, utilityShape } from "@/lib/format";
import UtilityMarker from "./UtilityMarker";

const ProjectMap = dynamic(() => import("./ProjectMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-slate-100" />,
});

interface Props {
  projects: Project[];
  utilities: string[];
  selected: Opportunity | null;
  onSelectProject?: (projectId: string) => void;
}

export default function MapPanel({ projects, utilities, selected, onSelectProject }: Props) {
  const unmapped = projects.filter((p) => p.latitude == null || p.longitude == null).length;
  const hasApprox = projects.some((p) => p.geometry && p.geometry_precision !== "route");
  const hasRoute = projects.some((p) => p.geometry && p.geometry_precision === "route");

  return (
    <section className="relative h-[420px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm lg:h-full lg:min-h-[520px]">
      <ProjectMap projects={projects} selected={selected} onSelectProject={onSelectProject} />
      <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] space-y-1 rounded-lg border border-slate-200 bg-white/95 px-3 py-2 text-xs text-slate-700 shadow-sm">
        {utilities.map((u) => (
          <p key={u} className="flex items-center gap-2">
            <UtilityMarker shape={utilityShape(u)} color={utilityColor(u)} />
            {shortUtility(u)} projects
          </p>
        ))}
        {hasRoute && (
          <p className="flex items-center gap-2">
            <span className="w-5 border-t-[3px] border-slate-500" /> Mapped route
          </p>
        )}
        {hasApprox && (
          <p className="flex items-center gap-2">
            <span className="w-5 border-t-[3px] border-dotted border-slate-500" /> Approximate corridor
          </p>
        )}
        {selected && (
          <p className="flex items-center gap-2">
            <span className="w-5 border-t-2 border-dashed border-slate-900" /> Selected pair
          </p>
        )}
        {unmapped > 0 && <p className="text-slate-500">{unmapped} without location (list only)</p>}
      </div>
      {projects.length === 0 && (
        <div className="pointer-events-none absolute inset-x-0 top-4 z-[1000] mx-auto w-fit rounded-lg bg-white/95 px-3 py-1.5 text-xs text-slate-600 shadow-sm">
          Run an analysis to see project locations
        </div>
      )}
    </section>
  );
}

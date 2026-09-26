"use client";

import type { Opportunity } from "@/lib/types";
import { fmtMiles, fmtMonths, shortUtility, utilityColor, utilityShape } from "@/lib/format";
import UtilityMarker from "./UtilityMarker";
import ScoreBadge from "./ScoreBadge";

interface Props {
  opportunities: Opportunity[];
  rankOf: Map<string, number>;
  selectedId: string | null;
  onSelect: (id: string) => void;
  total: number; // before filters, to tell "none found" apart from "all filtered out"
  onResetFilters: () => void;
}

function ProjectLine({ utility, name }: { utility: string; name: string }) {
  return (
    <p className="flex items-center gap-2 truncate text-sm text-slate-900">
      <UtilityMarker shape={utilityShape(utility)} color={utilityColor(utility)} />
      <span className="shrink-0 font-semibold">{shortUtility(utility)}</span>
      <span className="truncate">{name}</span>
    </p>
  );
}

export default function OpportunityList({ opportunities, rankOf, selectedId, onSelect, total, onResetFilters }: Props) {
  if (opportunities.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
        {total === 0 ? (
          "The analysis found no coordination opportunities between these utilities."
        ) : (
          <>
            All {total} opportunities are hidden by the current filters.{" "}
            <button type="button" onClick={onResetFilters} className="font-semibold text-slate-900 underline">
              Reset filters
            </button>
          </>
        )}
      </div>
    );
  }

  return (
    <ol className="flex flex-col gap-2">
      {opportunities.map((o) => {
        const active = o.id === selectedId;
        const overlap = o.features.schedule_overlap_months;
        return (
          <li key={o.id}>
            <button
              type="button"
              onClick={() => onSelect(o.id)}
              aria-pressed={active}
              className={`w-full rounded-xl border p-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 ${
                active
                  ? "border-slate-900 bg-slate-50 ring-1 ring-slate-900"
                  : "border-slate-200 bg-white hover:border-slate-400"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="text-xs font-semibold text-slate-400">#{rankOf.get(o.id)}</p>
                  <ProjectLine utility={o.project_a.utility} name={o.project_a.project_name} />
                  <p className="pl-4 text-xs text-slate-400">↕</p>
                  <ProjectLine utility={o.project_b.utility} name={o.project_b.project_name} />
                </div>
                <ScoreBadge score={o.coordination_score} />
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
                <span>
                  {o.features.distance_miles == null ? "Distance: not available" : `${fmtMiles(o.features.distance_miles)} apart`}
                </span>
                <span>
                  {overlap == null ? "Schedule: not available" : overlap === 0 ? "No schedule overlap" : `${fmtMonths(overlap)} schedule overlap`}
                </span>
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

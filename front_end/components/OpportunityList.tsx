"use client";

import type { Opportunity, Project } from "@/lib/types";
import { fmtMiles, fmtScheduleGap, humanize, NA, utilityColor, utilityShape } from "@/lib/format";
import UtilityMarker from "./UtilityMarker";
import ScoreBadge from "./ScoreBadge";

interface Props {
  opportunities: Opportunity[];
  onSelect: (id: string) => void;
  total: number; // before filters, to tell "none found" apart from "all filtered out"
  onResetFilters: () => void;
}

function ProjectLine({ p }: { p: Project }) {
  return (
    <p className="flex min-w-0 items-baseline gap-2">
      <UtilityMarker shape={utilityShape(p.utility)} color={utilityColor(p.utility)} />
      <span className="min-w-0 break-words">{p.name}</span>
    </p>
  );
}

export default function OpportunityList({ opportunities, onSelect, total, onResetFilters }: Props) {
  if (opportunities.length === 0) {
    return (
      <p className="px-4 py-6 text-graphite">
        {total === 0 ? (
          "No project pairs had enough data to score."
        ) : (
          <>
            The filters hide all {total} pairs.{" "}
            <button type="button" onClick={onResetFilters} className="font-semibold text-ink underline">
              Clear filters
            </button>
          </>
        )}
      </p>
    );
  }

  return (
    <ol>
      {opportunities.map((o) => {
        const a = o.analysis;
        const gap = fmtScheduleGap(a);
        const typeLabel =
          o.project_a.project_type === o.project_b.project_type
            ? humanize(o.project_a.project_type)
            : `${humanize(o.project_a.project_type)} and ${humanize(o.project_b.project_type)}`;
        return (
          <li key={o.opportunity_id} className="group relative border-b border-rule">
            <span
              aria-hidden
              className="absolute inset-y-0 left-0 w-[3px] scale-y-0 bg-ink transition-transform duration-150 group-hover:scale-y-100 group-focus-visible:scale-y-100"
            />
            <button
              type="button"
              onClick={() => onSelect(o.opportunity_id)}
              className="no-press-scale grid w-full grid-cols-[2.25rem_minmax(0,1fr)_auto] items-start gap-x-3 px-4 py-3 text-left hover:bg-sheet active:bg-rule"
            >
              <span className="mt-0.5 grid h-7 w-7 place-items-center rounded-md border border-graphite font-display text-sm leading-none font-semibold text-graphite group-hover:border-ink group-hover:text-ink">
                {a.opportunity_rank}
              </span>
              <span className="min-w-0 space-y-0.5">
                <ProjectLine p={o.project_a} />
                <ProjectLine p={o.project_b} />
                <span className="block pt-1 text-sm text-graphite">{typeLabel}</span>
                <span className="block text-sm text-graphite">
                  {a.distance_miles == null ? "Distance not available" : `${fmtMiles(a.distance_miles)} apart`}
                  {gap !== NA && `, ${gap.toLowerCase()}`}
                </span>
              </span>
              <ScoreBadge score={a.coordination_score} />
            </button>
          </li>
        );
      })}
    </ol>
  );
}

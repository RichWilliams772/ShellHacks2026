"use client";

import { humanize } from "@/lib/format";

export interface FilterState {
  year: number | "all";
  projectType: string | "all";
  maxDistance: number; // miles; ANY_DISTANCE means no limit
  minScore: number;
}

// Top of the slider = no distance limit, so far-apart pairs are never unreachable.
export const ANY_DISTANCE = 100;

export const DEFAULT_FILTERS: FilterState = {
  year: "all",
  projectType: "all",
  maxDistance: ANY_DISTANCE,
  minScore: 0,
};

interface Props {
  value: FilterState;
  onChange: (v: FilterState) => void;
  years: number[];
  projectTypes: string[];
}

export default function Filters({ value, onChange, years, projectTypes }: Props) {
  const set = <K extends keyof FilterState>(k: K, v: FilterState[K]) => onChange({ ...value, [k]: v });
  const label = "text-sm text-graphite";
  const input = "mt-1 w-full rounded-lg border border-rule bg-sheet px-2 py-1 text-ink";

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-3 border-b border-ink px-4 py-3">
      <label className={label}>
        Active in
        <select
          className={input}
          value={value.year}
          onChange={(e) => set("year", e.target.value === "all" ? "all" : Number(e.target.value))}
        >
          <option value="all">Any year</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </label>
      <label className={label}>
        Project type
        <select className={input} value={value.projectType} onChange={(e) => set("projectType", e.target.value)}>
          <option value="all">Any type</option>
          {projectTypes.map((t) => (
            <option key={t} value={t}>
              {humanize(t)}
            </option>
          ))}
        </select>
      </label>
      <label className={label}>
        Within <span className="font-semibold text-ink">{value.maxDistance >= ANY_DISTANCE ? "any distance" : `${value.maxDistance} mi`}</span>
        <input
          type="range"
          min={5}
          max={ANY_DISTANCE}
          step={5}
          value={value.maxDistance}
          onChange={(e) => set("maxDistance", Number(e.target.value))}
          className="mt-2 w-full accent-ink"
        />
      </label>
      <label className={label}>
        Score at least <span className="font-semibold text-ink">{value.minScore}</span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={value.minScore}
          onChange={(e) => set("minScore", Number(e.target.value))}
          className="mt-2 w-full accent-ink"
        />
      </label>
    </div>
  );
}

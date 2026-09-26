"use client";

import { humanize } from "@/lib/format";

export interface FilterState {
  year: number | "all";
  projectType: string | "all";
  maxDistance: number; // miles
  minScore: number;
}

export const DEFAULT_FILTERS: FilterState = {
  year: "all",
  projectType: "all",
  maxDistance: 50,
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
  const inputCls = "w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900";

  return (
    <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-200 bg-white p-3">
      <label className="text-xs font-medium text-slate-600">
        Year
        <select
          className={`mt-1 ${inputCls}`}
          value={value.year}
          onChange={(e) => set("year", e.target.value === "all" ? "all" : Number(e.target.value))}
        >
          <option value="all">All years</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs font-medium text-slate-600">
        Project type
        <select
          className={`mt-1 ${inputCls}`}
          value={value.projectType}
          onChange={(e) => set("projectType", e.target.value)}
        >
          <option value="all">All types</option>
          {projectTypes.map((t) => (
            <option key={t} value={t}>
              {humanize(t)}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs font-medium text-slate-600">
        Max distance: <span className="tabular-nums text-slate-900">{value.maxDistance} mi</span>
        <input
          type="range"
          min={5}
          max={100}
          step={5}
          value={value.maxDistance}
          onChange={(e) => set("maxDistance", Number(e.target.value))}
          className="mt-2 w-full accent-slate-900"
        />
      </label>
      <label className="text-xs font-medium text-slate-600">
        Min score: <span className="tabular-nums text-slate-900">{value.minScore}</span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={value.minScore}
          onChange={(e) => set("minScore", Number(e.target.value))}
          className="mt-2 w-full accent-slate-900"
        />
      </label>
    </div>
  );
}

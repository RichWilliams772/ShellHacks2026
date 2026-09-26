"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { AnalyzeResponse, Project } from "@/lib/types";
import { analyze, getProjects, getUtilities } from "@/lib/api";
import { DEFAULT_UTILITY_A, DEFAULT_UTILITY_B, USE_MOCK } from "@/lib/config";
import { years as yearsOf } from "@/lib/format";
import Header from "./Header";
import UtilityComparison from "./UtilityComparison";
import KpiCards from "./KpiCards";
import Filters, { ANY_DISTANCE, DEFAULT_FILTERS, type FilterState } from "./Filters";
import OpportunityList from "./OpportunityList";
import OpportunityDetail from "./OpportunityDetail";
import MapPanel from "./MapPanel";

type Status = "idle" | "loading" | "ready" | "error";

export default function Dashboard() {
  const [utilities, setUtilities] = useState<string[]>([DEFAULT_UTILITY_A, DEFAULT_UTILITY_B]);
  const [utilityA, setUtilityA] = useState(DEFAULT_UTILITY_A);
  const [utilityB, setUtilityB] = useState(DEFAULT_UTILITY_B);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [allProjects, setAllProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  // The pair the current results belong to; the dropdowns may change after an analysis.
  const [analyzed, setAnalyzed] = useState<[string, string]>([DEFAULT_UTILITY_A, DEFAULT_UTILITY_B]);
  const detailRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getUtilities()
      .then((list) => list.length >= 2 && setUtilities(list))
      .catch(() => {}); // keep defaults if the backend isn't up yet
  }, []);

  async function runAnalysis() {
    const pair: [string, string] = [utilityA, utilityB];
    setStatus("loading");
    setError(null);
    setSelectedId(null);
    try {
      const [res, projects] = await Promise.all([
        analyze({ utility_a: pair[0], utility_b: pair[1] }),
        getProjects(),
      ]);
      setAnalyzed(pair);
      setData(res);
      setAllProjects(projects);
      setFilters(DEFAULT_FILTERS);
      setStatus("ready");
    } catch (e) {
      console.error("GridSync analysis failed:", e); // details for developers only
      setError("GridSync couldn't complete the analysis. Please try again.");
      setStatus("error");
    }
  }

  const opportunities = useMemo(() => data?.opportunities ?? [], [data]);

  // Rank = position in the backend's score order (stable even when filters hide some).
  const rankOf = useMemo(() => {
    const sorted = [...opportunities].sort((a, b) => b.coordination_score - a.coordination_score);
    return new Map(sorted.map((o, i) => [o.id, i + 1]));
  }, [opportunities]);

  const filterOptions = useMemo(() => {
    const ys = new Set<number>();
    const types = new Set<string>();
    for (const o of opportunities) {
      for (const p of [o.project_a, o.project_b]) {
        yearsOf(p.start_date, p.end_date).forEach((y) => ys.add(y));
        if (p.project_type) types.add(p.project_type);
      }
    }
    return { years: [...ys].sort(), types: [...types].sort() };
  }, [opportunities]);

  // Filtering only hides rows; it never changes any number from the backend.
  const filtered = useMemo(() => {
    return opportunities
      .filter((o) => {
        const d = o.features.distance_miles;
        if (d != null && filters.maxDistance < ANY_DISTANCE && d > filters.maxDistance) return false; // unknown distance stays visible
        if (o.coordination_score < filters.minScore) return false;
        if (filters.projectType !== "all" && o.project_a.project_type !== filters.projectType && o.project_b.project_type !== filters.projectType)
          return false;
        if (filters.year !== "all") {
          const y = filters.year;
          const inYear = [o.project_a, o.project_b].some((p) => yearsOf(p.start_date, p.end_date).includes(y));
          if (!inYear) return false;
        }
        return true;
      })
      .sort((a, b) => b.coordination_score - a.coordination_score);
  }, [opportunities, filters]);

  const selected = opportunities.find((o) => o.id === selectedId) ?? null;

  // Map shows every project from the two utilities; falls back to projects inside opportunities.
  const mapProjects = useMemo(() => {
    const byId = new Map<string, Project>();
    const wanted = new Set(analyzed);
    for (const p of allProjects) if (wanted.has(p.utility)) byId.set(p.id, p);
    for (const o of opportunities) {
      byId.set(o.project_a.id, o.project_a);
      byId.set(o.project_b.id, o.project_b);
    }
    return [...byId.values()];
  }, [allProjects, opportunities, analyzed]);

  const isDemo = USE_MOCK || mapProjects.some((p) => p.data_type === "demo");

  function select(id: string) {
    setSelectedId(id);
    setTimeout(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  function selectByProject(projectId: string) {
    // Clicking a marker opens its popup and focuses its strongest opportunity, without scrolling away from the map.
    const best = filtered.find((o) => o.project_a.id === projectId || o.project_b.id === projectId);
    if (best) setSelectedId(best.id);
  }

  const loading = status === "loading";
  const ready = status === "ready";

  return (
    <div className="min-h-screen bg-slate-100">
      <Header demo={isDemo} />
      <main className="mx-auto flex max-w-[1400px] flex-col gap-4 px-4 py-5 sm:px-6">
        <UtilityComparison
          utilities={utilities}
          utilityA={utilityA}
          utilityB={utilityB}
          onChangeA={setUtilityA}
          onChangeB={setUtilityB}
          onAnalyze={runAnalysis}
          loading={loading}
        />

        {status === "error" && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <span>{error}</span>
            <button
              type="button"
              onClick={runAnalysis}
              className="rounded-md border border-red-300 bg-white px-3 py-1.5 font-medium hover:bg-red-100"
            >
              Retry
            </button>
          </div>
        )}

        <KpiCards
          loading={loading}
          projectsAnalyzed={ready ? data!.projects_analyzed : null}
          opportunities={ready ? opportunities.length : null}
          highestScore={ready && opportunities.length > 0 ? Math.round(Math.max(...opportunities.map((o) => o.coordination_score))) : null}
          utilitiesCompared={ready ? 2 : null}
        />

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_400px]">
          <MapPanel
            projects={ready ? mapProjects : []}
            utilities={ready ? analyzed : [utilityA, utilityB]}
            selected={selected}
            onSelectProject={selectByProject}
          />

          <aside className="flex flex-col gap-3 lg:max-h-[640px]">
            {ready && (
              <Filters value={filters} onChange={setFilters} years={filterOptions.years} projectTypes={filterOptions.types} />
            )}
            <div className="flex items-baseline justify-between px-1">
              <h2 className="text-sm font-semibold text-slate-900">Ranked coordination opportunities</h2>
              {ready && (
                <span className="text-xs text-slate-500">
                  {filtered.length} of {opportunities.length} shown
                  {data!.pairs_evaluated != null && ` · ${data!.pairs_evaluated.toLocaleString()} pairs evaluated`}
                </span>
              )}
            </div>
            <div className="max-h-[520px] min-h-0 flex-1 overflow-y-auto pr-1 lg:max-h-none">
              {status === "idle" && (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
                  Choose two utilities and click <span className="font-semibold text-slate-700">Analyze Opportunities</span> to
                  find where their planned projects overlap.
                </div>
              )}
              {loading && (
                <div className="flex flex-col gap-2" role="status">
                  <p className="px-1 text-sm text-slate-500">Analyzing project overlap…</p>
                  {[0, 1, 2, 3].map((i) => (
                    <div key={i} className="h-28 animate-pulse rounded-xl bg-white" />
                  ))}
                </div>
              )}
              {ready && (
                <OpportunityList
                  opportunities={filtered}
                  rankOf={rankOf}
                  selectedId={selectedId}
                  onSelect={select}
                  total={opportunities.length}
                  onResetFilters={() => setFilters(DEFAULT_FILTERS)}
                />
              )}
            </div>
          </aside>
        </div>

        <div ref={detailRef} className="scroll-mt-4">
          {selected && <OpportunityDetail o={selected} rank={rankOf.get(selected.id)} onClose={() => setSelectedId(null)} />}
        </div>
      </main>
    </div>
  );
}

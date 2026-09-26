"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { AnalyzeResponse, Project } from "@/lib/types";
import { analyze } from "@/lib/api";
import { API_URL, UTILITY_A, UTILITY_B, USE_MOCK } from "@/lib/config";
import { projectYears } from "@/lib/format";
import TitleBlock from "./TitleBlock";
import Filters, { ANY_DISTANCE, DEFAULT_FILTERS, type FilterState } from "./Filters";
import OpportunityList from "./OpportunityList";
import OpportunityDetail from "./OpportunityDetail";
import MapPanel from "./MapPanel";

type Status = "idle" | "loading" | "ready" | "error";

export default function Dashboard() {
  const [status, setStatus] = useState<Status>("idle");
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const sideRef = useRef<HTMLElement>(null);

  async function runAnalysis() {
    setStatus("loading");
    setSelectedId(null);
    try {
      const { data: result } = await analyze({ utility_a: UTILITY_A, utility_b: UTILITY_B });
      setData(result);
      setFilters(DEFAULT_FILTERS);
      setStatus("ready");
    } catch (e) {
      console.error("GridSync analysis failed:", e);
      setStatus("error");
    }
  }

  const opportunities = useMemo(() => data?.opportunities ?? [], [data]);

  const filterOptions = useMemo(() => {
    const ys = new Set<number>();
    const types = new Set<string>();
    for (const o of opportunities)
      for (const p of [o.project_a, o.project_b]) {
        projectYears(p).forEach((y) => ys.add(y));
        types.add(p.project_type);
      }
    return { years: [...ys].sort(), types: [...types].sort() };
  }, [opportunities]);

  // Filtering only hides rows; it never changes a number from the analysis.
  const filtered = useMemo(
    () =>
      opportunities
        .filter((o) => {
          const d = o.analysis.distance_miles;
          if (d != null && filters.maxDistance < ANY_DISTANCE && d > filters.maxDistance) return false;
          if (o.analysis.coordination_score < filters.minScore) return false;
          if (filters.projectType !== "all" && ![o.project_a, o.project_b].some((p) => p.project_type === filters.projectType))
            return false;
          if (filters.year !== "all" && ![o.project_a, o.project_b].some((p) => projectYears(p).includes(filters.year as number)))
            return false;
          return true;
        })
        .sort((x, y) => x.analysis.opportunity_rank - y.analysis.opportunity_rank),
    [opportunities, filters],
  );

  const selected = opportunities.find((o) => o.opportunity_id === selectedId) ?? null;

  // Every project that appears in an opportunity, once.
  const mapProjects = useMemo(() => {
    const byId = new Map<string, Project>();
    for (const o of opportunities) for (const p of [o.project_a, o.project_b]) byId.set(p.id, p);
    return [...byId.values()];
  }, [opportunities]);

  // Opening or leaving a pair starts the side column at the top.
  // Block body on purpose: an implicit-return arrow here would make the effect's
  // return value whatever scrollTo() hands back, and React treats any non-function,
  // non-undefined return as an attempted cleanup function.
  useEffect(() => {
    sideRef.current?.scrollTo({ top: 0 });
  }, [selectedId]);

  function selectByProject(projectId: string) {
    const best = filtered.find((o) => o.project_a.id === projectId || o.project_b.id === projectId);
    if (best) setSelectedId(best.opportunity_id);
  }

  const ready = status === "ready";

  return (
    <div className="flex min-h-screen flex-col lg:h-screen">
      <TitleBlock summary={ready ? data!.summary : null} loading={status === "loading"} onAnalyze={runAnalysis} />

      <main className="grid flex-1 lg:min-h-0 lg:grid-cols-[minmax(0,1fr)_440px]">
        <MapPanel projects={ready ? mapProjects : []} selected={selected} onSelectProject={selectByProject} />

        <aside ref={sideRef} className="border-t border-ink lg:overflow-y-auto lg:border-t-0 lg:border-l">
          {status === "idle" && (
            <p className="px-4 py-6 text-graphite">
              Run the analysis to rank every Duke and TECO project pair by how closely their location, schedule, and
              type line up.
            </p>
          )}
          {status === "loading" && (
            <p className="px-4 py-6 text-graphite" role="status">
              Comparing project pairs…
            </p>
          )}
          {status === "error" && (
            <div className="px-4 py-6">
              <p>
                {USE_MOCK
                  ? "The saved analysis results couldn't be loaded."
                  : `Couldn't get results from the analysis service at ${API_URL}. Check that the backend is running, then try again.`}
              </p>
              <button type="button" onClick={runAnalysis} className="mt-3 font-semibold underline">
                Try again
              </button>
            </div>
          )}
          {ready &&
            (selected ? (
              <OpportunityDetail o={selected} onBack={() => setSelectedId(null)} />
            ) : (
              <>
                <Filters value={filters} onChange={setFilters} years={filterOptions.years} projectTypes={filterOptions.types} />
                <p className="flex items-baseline justify-between border-b border-rule px-4 py-2">
                  <span className="font-display text-xl font-semibold">Ranked pairs</span>
                  <span className="text-sm text-graphite">
                    {filtered.length} of {opportunities.length}
                  </span>
                </p>
                <OpportunityList
                  opportunities={filtered}
                  onSelect={setSelectedId}
                  total={opportunities.length}
                  onResetFilters={() => setFilters(DEFAULT_FILTERS)}
                />
              </>
            ))}
        </aside>
      </main>
    </div>
  );
}

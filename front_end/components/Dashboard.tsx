"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent } from "react";
import type { AnalyzeResponse, Project } from "@/lib/types";
import { analyze } from "@/lib/api";
import { API_URL, UTILITY_A, UTILITY_B, USE_MOCK } from "@/lib/config";
import { projectYears } from "@/lib/format";
import TitleBlock from "./TitleBlock";
import Filters, { ANY_DISTANCE, DEFAULT_FILTERS, type FilterState } from "./Filters";
import OpportunityList from "./OpportunityList";
import OpportunityDetail from "./OpportunityDetail";
import MapPanel from "./MapPanel";
import AnalysisProgress from "./AnalysisProgress";

type Status = "idle" | "loading" | "ready" | "error";

// The mock snapshot resolves in a few milliseconds - too fast to ever see the checklist
// AnalysisProgress draws. Holding "loading" open for at least this long means a click on
// "Analyze projects" always shows the real, ordered comparison it just asked for, whether
// the answer came back instantly (mock) or took a couple of seconds (live backend).
const MIN_LOADING_MS = 1150;
const ANALYSIS_DEFAULT = 440;
const ANALYSIS_MIN = 280;
const MAP_MIN = 360;
const DIVIDER = 12;
const KEY_STEP = 24;

function clampAnalysis(width: number, containerWidth: number) {
  const max = Math.max(ANALYSIS_MIN, containerWidth - MAP_MIN - DIVIDER);
  return Math.min(max, Math.max(ANALYSIS_MIN, Math.round(width)));
}

export default function Dashboard() {
  const [status, setStatus] = useState<Status>("idle");
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [analyzedAt, setAnalyzedAt] = useState<Date | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const sideRef = useRef<HTMLDivElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const dividerRef = useRef<HTMLDivElement>(null);
  const [analysisWidth, setAnalysisWidth] = useState(ANALYSIS_DEFAULT);
  const [analysisMax, setAnalysisMax] = useState(ANALYSIS_DEFAULT);

  async function runAnalysis() {
    setStatus("loading");
    setSelectedId(null);
    try {
      const [{ data: result }] = await Promise.all([
        analyze({ utility_a: UTILITY_A, utility_b: UTILITY_B }),
        new Promise((resolve) => setTimeout(resolve, MIN_LOADING_MS)),
      ]);
      setData(result);
      setAnalyzedAt(new Date());
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

  function clampToMain(width: number) {
    const container = mainRef.current?.clientWidth ?? 0;
    if (container <= 0) return Math.max(ANALYSIS_MIN, Math.round(width));
    return clampAnalysis(width, container);
  }

  useEffect(() => {
    const el = mainRef.current;
    if (!el) return;
    const measure = () => {
      if (!window.matchMedia("(min-width: 1024px)").matches) return;
      const max = Math.max(ANALYSIS_MIN, el.clientWidth - MAP_MIN - DIVIDER);
      setAnalysisMax(max);
      setAnalysisWidth((width) => clampAnalysis(width, el.clientWidth));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const analysisWidthFromPointer = useCallback((clientX: number) => {
    const main = mainRef.current;
    if (!main) return;
    const rect = main.getBoundingClientRect();
    setAnalysisWidth(clampAnalysis(rect.right - clientX - DIVIDER / 2, rect.width));
  }, []);

  useEffect(() => {
    const el = dividerRef.current;
    if (!el) return;
    let pointerId: number | null = null;
    const move = (event: globalThis.PointerEvent) => {
      if (pointerId === null || event.pointerId !== pointerId) return;
      analysisWidthFromPointer(event.clientX);
    };
    const up = (event: globalThis.PointerEvent) => {
      if (pointerId === null || event.pointerId !== pointerId) return;
      pointerId = null;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    const down = (event: globalThis.PointerEvent) => {
      if (event.button !== 0) return;
      pointerId = event.pointerId;
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    };
    el.addEventListener("pointerdown", down);
    return () => {
      el.removeEventListener("pointerdown", down);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, [analysisWidthFromPointer]);

  function onDividerKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setAnalysisWidth((width) => clampToMain(width + KEY_STEP));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setAnalysisWidth((width) => clampToMain(width - KEY_STEP));
    }
  }

  function selectByProject(projectId: string) {
    const best = filtered.find((o) => o.project_a.id === projectId || o.project_b.id === projectId);
    if (best) setSelectedId(best.opportunity_id);
  }

  const ready = status === "ready";

  return (
    <div className="flex min-h-screen flex-col lg:h-screen">
      <TitleBlock
        summary={ready ? data!.summary : null}
        analyzedAt={ready ? analyzedAt : null}
        loading={status === "loading"}
        onAnalyze={runAnalysis}
      />

      <main
        ref={mainRef}
        className="flex flex-1 flex-col lg:min-h-0 lg:flex-row"
        style={{ "--gs-analysis": `${analysisWidth}px` } as CSSProperties}
      >
        <div className="min-w-0 lg:h-full lg:min-h-0 lg:min-w-[360px] lg:flex-1 lg:basis-0">
          <MapPanel
            projects={ready ? mapProjects : []}
            selected={selected}
            onSelectProject={selectByProject}
            opportunities={ready ? filtered : []}
          />
        </div>

        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize the map and analysis panels. Left arrow widens the analysis panel."
          aria-valuemin={ANALYSIS_MIN}
          aria-valuemax={analysisMax}
          aria-valuenow={analysisWidth}
          aria-valuetext={`${analysisWidth} pixel analysis panel`}
          tabIndex={0}
          ref={dividerRef}
          className="relative hidden w-3 shrink-0 cursor-col-resize touch-none select-none items-center justify-center bg-sheet lg:flex"
          onKeyDown={onDividerKeyDown}
        >
          <span aria-hidden className="h-12 w-px bg-ink" />
        </div>

        <aside
          className="flex flex-col border-t border-ink lg:min-h-0 lg:w-[var(--gs-analysis)] lg:shrink-0 lg:border-t-0 lg:border-l"
          data-analysis-width={analysisWidth}
        >
          <div ref={sideRef} className="min-h-0 flex-1 lg:overflow-y-auto">
          {status === "idle" && (
            <p className="px-4 py-6 text-graphite">
              Run the analysis to rank every Duke and TECO project pair by how closely their location, schedule, and
              type line up.
            </p>
          )}
          {status === "loading" && <AnalysisProgress />}
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
          {ready && (
            <div key={selected ? selected.opportunity_id : "list"} className="panel-in">
              {selected ? (
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
              )}
            </div>
          )}
          </div>
        </aside>
      </main>
    </div>
  );
}

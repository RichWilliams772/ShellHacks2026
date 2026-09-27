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
import ChatPanel from "./ChatPanel";

type Status = "idle" | "loading" | "ready" | "error";

const ANALYSIS_DEFAULT = 440;
const ANALYSIS_MIN = 280;
const MAP_MIN = 360;
const DIVIDER = 12;
const KEY_STEP = 24;
const CHAT_DEFAULT = 240;
const CHAT_MIN = 168;
const DETAILS_MIN = 240;

function clampAnalysis(width: number, containerWidth: number) {
  const max = Math.max(ANALYSIS_MIN, containerWidth - MAP_MIN - DIVIDER);
  return Math.min(max, Math.max(ANALYSIS_MIN, Math.round(width)));
}

function clampChat(height: number, asideHeight: number) {
  const max = Math.max(CHAT_MIN, asideHeight - DETAILS_MIN - DIVIDER);
  return Math.min(max, Math.max(CHAT_MIN, Math.round(height)));
}

export default function Dashboard() {
  const [status, setStatus] = useState<Status>("idle");
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const sideRef = useRef<HTMLDivElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const asideRef = useRef<HTMLElement>(null);
  const dividerRef = useRef<HTMLDivElement>(null);
  const chatDividerRef = useRef<HTMLDivElement>(null);
  const [analysisWidth, setAnalysisWidth] = useState(ANALYSIS_DEFAULT);
  const [analysisMax, setAnalysisMax] = useState(ANALYSIS_DEFAULT);
  const [chatHeight, setChatHeight] = useState(CHAT_DEFAULT);
  const [chatMax, setChatMax] = useState(CHAT_DEFAULT);

  function clampToMain(width: number) {
    const container = mainRef.current?.clientWidth ?? 0;
    if (container <= 0) return Math.max(ANALYSIS_MIN, Math.round(width));
    return clampAnalysis(width, container);
  }

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
  // On a phone the page itself scrolls, so bring that column to the top of the screen.
  // Block body on purpose: an implicit-return arrow here would make the effect's
  // return value whatever scrollTo() hands back, and React treats any non-function,
  // non-undefined return as an attempted cleanup function.
  const skipInitialScroll = useRef(true);
  useEffect(() => {
    if (skipInitialScroll.current) {
      skipInitialScroll.current = false;
      return;
    }
    const el = sideRef.current;
    if (!el) return;
    if (el.scrollHeight > el.clientHeight + 1) {
      el.scrollTo({ top: 0 });
      return;
    }
    el.scrollIntoView({ block: "start" });
  }, [selectedId]);

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

  const chatHeightFromPointer = useCallback((clientY: number) => {
    const aside = asideRef.current;
    if (!aside) return;
    const rect = aside.getBoundingClientRect();
    setChatHeight(clampChat(rect.bottom - clientY - DIVIDER / 2, rect.height));
  }, []);

  useEffect(() => {
    const el = chatDividerRef.current;
    if (!el) return;
    let pointerId: number | null = null;
    const move = (event: globalThis.PointerEvent) => {
      if (pointerId === null || event.pointerId !== pointerId) return;
      chatHeightFromPointer(event.clientY);
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
  }, [chatHeightFromPointer, selectedId]);

  useEffect(() => {
    const el = asideRef.current;
    if (!el || !selectedId) return;
    const measure = () => {
      if (!window.matchMedia("(min-width: 1024px)").matches) return;
      const max = Math.max(CHAT_MIN, el.clientHeight - DETAILS_MIN - DIVIDER);
      setChatMax(max);
      setChatHeight((height) => clampChat(height, el.clientHeight));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [selectedId]);

  function onChatDividerKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const aside = asideRef.current;
    const limit = aside?.clientHeight ?? 0;
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setChatHeight((height) => clampChat(height + KEY_STEP, limit));
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setChatHeight((height) => clampChat(height - KEY_STEP, limit));
    }
  }

  function selectByProject(projectId: string) {
    const best = filtered.find((o) => o.project_a.id === projectId || o.project_b.id === projectId);
    if (best) setSelectedId(best.opportunity_id);
  }

  const ready = status === "ready";

  return (
    <div className="flex min-h-dvh min-w-0 flex-col overflow-x-clip pb-[env(safe-area-inset-bottom)] lg:h-screen lg:pb-0">
      <TitleBlock summary={ready ? data!.summary : null} loading={status === "loading"} onAnalyze={runAnalysis} />

      <main
        ref={mainRef}
        className="flex min-w-0 flex-1 flex-col lg:min-h-0 lg:flex-row"
        style={{ "--gs-analysis": `${analysisWidth}px` } as CSSProperties}
      >
        <MapPanel
          projects={ready ? mapProjects : []}
          selected={selected}
          onSelectProject={selectByProject}
          opportunities={ready ? filtered : []}
        />

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
          className="gs-split relative hidden w-3 shrink-0 cursor-col-resize touch-none select-none items-center justify-center bg-sheet lg:flex"
          onKeyDown={onDividerKeyDown}
        >
          <span aria-hidden className="h-12 w-1 rounded-full bg-cyan" />
        </div>

        <aside
          ref={asideRef}
          className="flex min-w-0 flex-col border-t border-rule bg-sheet lg:min-h-0 lg:w-[var(--gs-analysis)] lg:shrink-0 lg:overflow-hidden lg:border-t-0"
          data-analysis-width={analysisWidth}
          style={{ "--gs-chat": `${chatHeight}px` } as CSSProperties}
        >
          <div ref={sideRef} className="min-h-0 lg:min-h-[240px] lg:flex-1 lg:overflow-y-auto">
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
              <button type="button" onClick={runAnalysis} className="mt-3 font-semibold text-cyan underline">
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
          </div>
          {ready && selected && (
            <div
              role="separator"
              aria-orientation="horizontal"
              aria-label="Resize the opportunity details and chat. Up arrow gives the chat more height."
              aria-valuemin={CHAT_MIN}
              aria-valuemax={chatMax}
              aria-valuenow={chatHeight}
              aria-valuetext={`${chatHeight} pixel chat panel`}
              tabIndex={0}
              ref={chatDividerRef}
              className="gs-split relative hidden h-3 shrink-0 cursor-row-resize touch-none select-none items-center justify-center bg-sheet lg:flex"
              onKeyDown={onChatDividerKeyDown}
            >
              <span aria-hidden className="h-1 w-12 rounded-full bg-cyan" />
            </div>
          )}
          {ready && (
            <div className={selected ? "lg:h-[var(--gs-chat)] lg:min-h-0 lg:shrink-0 lg:overflow-hidden" : undefined}>
              <ChatPanel
                key={selected?.opportunity_id ?? "all"}
                opportunityId={selected?.opportunity_id ?? null}
                docked={selected != null}
              />
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

"use client";

import type { Confidence, Opportunity, Project, Strength } from "@/lib/types";
import {
  CONFIDENCE_HELP,
  SCORE_HELP,
  fmtInt,
  fmtKv,
  fmtMiles,
  fmtMoney,
  fmtMonths,
  fmtPct,
  fmtPeriod,
  humanize,
  precisionLabel,
  NA,
  utilityColor,
  utilityShape,
} from "@/lib/format";
import ScoreBadge from "./ScoreBadge";
import InfoTip from "./InfoTip";
import UtilityMarker from "./UtilityMarker";

// ---------- small pieces ----------

function Row({ label, value, help }: { label: string; value: string; help?: string }) {
  return (
    <div className="flex justify-between gap-3 py-1 text-sm">
      <dt className="text-slate-500">
        {label}
        {help && <InfoTip text={help} />}
      </dt>
      <dd className={`text-right ${value === NA ? "italic text-slate-400" : "text-slate-900"}`}>{value}</dd>
    </div>
  );
}

const CONF_STYLE: Record<Confidence, string> = {
  HIGH: "text-emerald-700",
  MEDIUM: "text-amber-700",
  LOW: "text-red-700",
  UNKNOWN: "text-slate-500",
};

function ProjectColumn({ p, label }: { p: Project; label: string }) {
  const conf = p.location_confidence ?? null;
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <UtilityMarker shape={utilityShape(p.utility)} color={utilityColor(p.utility)} />
        {label} · {p.utility}
      </p>
      <p className="mt-1 font-semibold text-slate-900">{p.project_name}</p>
      {p.description && <p className="mt-1 text-sm text-slate-600">{p.description}</p>}
      <dl className="mt-2 divide-y divide-slate-100">
        <Row label="Project type" value={humanize(p.project_type)} />
        <Row label="Voltage" value={fmtKv(p.voltage_kv)} />
        <Row label="Construction" value={fmtPeriod(p.start_date, p.end_date)} />
        <Row label="Status" value={humanize(p.status)} />
        {p.capital_cost != null && <Row label="Capital cost" value={fmtMoney(p.capital_cost)} />}
        {p.customers_impacted != null && <Row label="Customers impacted" value={fmtInt(p.customers_impacted)} />}
        <div className="flex justify-between gap-3 py-1 text-sm">
          <dt className="text-slate-500">
            Location confidence
            <InfoTip text={CONFIDENCE_HELP} />
          </dt>
          <dd className={conf ? `font-semibold ${CONF_STYLE[conf]}` : "italic text-slate-400"}>{conf ?? NA}</dd>
        </div>
        {p.geometry && <Row label="Geometry" value={precisionLabel(p.geometry_precision)} />}
      </dl>
      <p className="mt-2 text-[11px] text-slate-400">ID {p.id}</p>
    </div>
  );
}

function Bar({ label, value, help }: { label: string; value: number | null | undefined; help?: string }) {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="text-slate-600">
          {label}
          {help && <InfoTip text={help} />}
        </span>
        <span className="font-semibold tabular-nums text-slate-900">{pct}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-slate-800 transition-[width] duration-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`font-semibold tabular-nums ${value === NA ? "text-slate-400" : "text-slate-900"}`}>{value}</p>
    </div>
  );
}

const STRENGTH_STYLE: Record<Strength, string> = {
  HIGH: "bg-emerald-50 text-emerald-800 border-emerald-300",
  MEDIUM: "bg-amber-50 text-amber-800 border-amber-300",
  LOW: "bg-slate-50 text-slate-600 border-slate-300",
};

function Sources({ projects }: { projects: Project[] }) {
  return (
    <ul className="space-y-1.5 text-sm">
      {projects.map((p) => (
        <li key={p.id} className="text-slate-700">
          <span className="font-medium">{p.id}:</span>{" "}
          {p.source_url ? (
            <a href={p.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">
              {p.source_name}
            </a>
          ) : (
            <span>{p.source_name}</span>
          )}
          {p.source_page != null && <span className="text-slate-500"> · p. {p.source_page}</span>}
          {p.retrieved_date && <span className="text-slate-500"> · retrieved {p.retrieved_date}</span>}
          {p.data_type === "demo" && (
            <span className="ml-2 rounded border border-amber-300 bg-amber-50 px-1.5 text-[11px] font-semibold text-amber-800">
              DEMO
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

// ---------- panel ----------

export default function OpportunityDetail({ o, rank, onClose }: { o: Opportunity; rank?: number; onClose: () => void }) {
  const f = o.features;
  const resources = o.coordination_package.resources;
  // Score components are shown only if the backend supplied them — never estimated here.
  const hasComponents = [f.distance_similarity, f.schedule_similarity, f.project_similarity, f.infrastructure_similarity].some(
    (v) => v != null,
  );

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      {/* Title + score */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Coordination opportunity {rank ? `#${rank}` : ""}
          </p>
          <h2 className="text-lg font-semibold text-slate-900">
            {o.project_a.project_name} <span className="text-slate-400">↔</span> {o.project_b.project_name}
          </h2>
        </div>
        <div className="flex items-start gap-3">
          <div className="text-right">
            <p className="text-xs text-slate-500">
              Coordination score
              <InfoTip text={SCORE_HELP} />
            </p>
            <ScoreBadge score={o.coordination_score} size="lg" />
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close details"
            className="rounded-md px-2 py-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Measurements + score breakdown */}
      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <div className="grid grid-cols-2 gap-2 self-start">
          <Metric label="Geographic distance" value={fmtMiles(f.distance_miles)} />
          <Metric label="Schedule overlap" value={fmtMonths(f.schedule_overlap_months)} />
          <Metric label="Project type similarity" value={fmtPct(f.project_type_similarity)} />
          <Metric label="Voltage similarity" value={fmtPct(f.voltage_similarity)} />
          {f.text_similarity != null && <Metric label="Description similarity (ML)" value={fmtPct(f.text_similarity)} />}
        </div>
        {hasComponents ? (
          <div className="space-y-3 rounded-lg border border-slate-200 p-3">
            <p className="text-sm font-semibold text-slate-900">Score breakdown</p>
            <Bar label="Geographic proximity" value={f.distance_similarity} />
            <Bar label="Schedule overlap" value={f.schedule_similarity} />
            <Bar label="Project similarity" value={f.project_similarity} />
            <Bar label="Infrastructure similarity" value={f.infrastructure_similarity} />
            <p className="text-[11px] text-slate-400">Components not listed were unavailable and treated as neutral by the analysis.</p>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-200 p-3 text-xs text-slate-500">
            Score component breakdown not provided by the analysis for this pair.
          </div>
        )}
      </div>

      {/* Why + shared resources */}
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Why this opportunity?</h3>
          {o.reasons.length > 0 ? (
            <ul className="mt-2 space-y-1.5">
              {o.reasons.map((r, i) => (
                <li key={i} className="flex gap-2 text-sm text-slate-700">
                  <span className="text-emerald-600">✓</span>
                  {r}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm italic text-slate-400">No reasons returned by the analysis.</p>
          )}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-slate-900">Potential shared resources</h3>
          <p className="text-xs text-slate-500">From GridSync&apos;s resource rules. Potential only, not a commitment.</p>
          {resources.length > 0 ? (
            <ul className="mt-2 grid gap-2 sm:grid-cols-2">
              {resources.map((r) => (
                <li key={r.name} className="rounded-lg border border-slate-200 px-3 py-2">
                  <p className="text-sm font-medium text-slate-800">{humanize(r.name)}</p>
                  {r.strength && (
                    <p className="mt-1 text-xs text-slate-500">
                      Potential:{" "}
                      <span className={`rounded border px-1.5 py-0.5 font-semibold ${STRENGTH_STYLE[r.strength]}`}>{r.strength}</span>
                    </p>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm italic text-slate-400">No shared resources identified for these project types.</p>
          )}
        </div>
      </div>

      {/* Side-by-side comparison */}
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <ProjectColumn p={o.project_a} label="Project A" />
        <ProjectColumn p={o.project_b} label="Project B" />
      </div>

      <div className="mt-5">
        <h3 className="text-sm font-semibold text-slate-900">Public data sources</h3>
        <div className="mt-2">
          <Sources projects={[o.project_a, o.project_b]} />
        </div>
      </div>

      <p className="mt-5 border-t border-slate-100 pt-3 text-xs text-slate-500">
        The coordination score shows the strength of a potential coordination opportunity. It is not a probability of
        coordination, a prediction of success, or a savings estimate. GridSync surfaces opportunities; planners decide.
      </p>
    </section>
  );
}

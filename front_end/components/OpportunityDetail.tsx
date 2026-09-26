"use client";

import type { Opportunity, Potential, Project } from "@/lib/types";
import {
  CONFIDENCE_HELP,
  SCORE_HELP,
  NA,
  fmtMiles,
  fmtSchedule,
  fmtScheduleGap,
  geometryLabel,
  humanize,
  utilityColor,
  utilityShape,
} from "@/lib/format";
import ScoreBadge from "./ScoreBadge";
import InfoTip from "./InfoTip";
import UtilityMarker from "./UtilityMarker";

function Heading({ children }: { children: React.ReactNode }) {
  return <h3 className="mt-6 mb-2 font-display text-xl font-semibold">{children}</h3>;
}

function Row({ label, value, help }: { label: string; value: string; help?: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-rule py-1.5 last:border-0">
      <dt className="shrink-0 text-graphite">
        {label}
        {help && <InfoTip text={help} />}
      </dt>
      <dd className={`text-right ${value === NA ? "text-graphite italic" : ""}`}>{value}</dd>
    </div>
  );
}

// 0–100 component from the pipeline. Missing components are left out, never drawn as zero.
function Bar({ label, value }: { label: string; value: number | null }) {
  if (value == null) return null;
  return (
    <div>
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="font-semibold">{Math.round(value)}</span>
      </div>
      <div className="mt-1 h-1.5 bg-rule">
        <div className="h-full bg-ink" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
    </div>
  );
}

const PIPS: Record<Potential, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };

function PotentialPips({ level }: { level: Potential }) {
  return (
    <span className="flex items-center gap-1" aria-label={`${humanize(level.toLowerCase())} potential`}>
      {[1, 2, 3].map((i) => (
        <span key={i} className={`h-2.5 w-2.5 ${i <= PIPS[level] ? "bg-ink" : "border border-graphite"}`} />
      ))}
      <span className="ml-1 w-14 text-sm text-graphite">{humanize(level.toLowerCase())}</span>
    </span>
  );
}

function ProjectFacts({ p }: { p: Project }) {
  const s = p.sources;
  return (
    <section className="mt-4">
      <p className="flex items-center gap-2 font-semibold">
        <UtilityMarker shape={utilityShape(p.utility)} color={utilityColor(p.utility)} />
        {p.name}
      </p>
      <p className="text-sm text-graphite">
        {p.utility}, {p.id}
      </p>
      <dl className="mt-1">
        <Row label="Type" value={humanize(p.project_type)} />
        <Row label="Voltage" value={p.voltage_label ?? NA} />
        <Row label="Schedule" value={fmtSchedule(p)} />
        <Row label="Status" value={p.status ?? NA} />
        <Row label="Location confidence" value={p.location_confidence ?? NA} help={CONFIDENCE_HELP} />
        <Row label="Mapped as" value={geometryLabel(p.geometry_type)} />
      </dl>
      <div className="mt-2 space-y-1 text-sm text-graphite">
        {s.project_source && <p>Project: {s.project_source}</p>}
        {s.circuit_endpoint_source && <p>Circuit endpoints: {s.circuit_endpoint_source}</p>}
        {s.geography_source && <p>Location: {s.geography_source}</p>}
        {s.source_url && (
          <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="text-ink underline">
            Open the project page
          </a>
        )}
      </div>
    </section>
  );
}

export default function OpportunityDetail({ o, onBack }: { o: Opportunity; onBack: () => void }) {
  const a = o.analysis;
  const resources = o.potential_shared_resources;

  return (
    <article className="px-4 pt-3 pb-8">
      <button type="button" onClick={onBack} className="text-graphite underline hover:text-ink">
        Back to all pairs
      </button>

      <div className="mt-4 flex items-end justify-between gap-4">
        <div>
          <p className="text-graphite">Pair {a.opportunity_rank} of the ranking</p>
          <p className="text-sm text-graphite">
            Coordination score
            <InfoTip text={SCORE_HELP} />
          </p>
        </div>
        <ScoreBadge score={a.coordination_score} size="lg" />
      </div>
      {a.score_confidence && (
        <p className="mt-1 text-right text-sm text-graphite">{humanize(a.score_confidence.toLowerCase())} confidence in the inputs</p>
      )}

      <h2 className="mt-4 font-display text-2xl leading-tight font-semibold">
        {o.project_a.name}
        <span className="block text-graphite">and {o.project_b.name}</span>
      </h2>

      <dl className="mt-4 grid grid-cols-2 gap-4 border-y border-ink py-3">
        <div>
          <dt className="text-sm text-graphite">Distance</dt>
          <dd className="font-display text-2xl font-semibold text-redline">{fmtMiles(a.distance_miles)}</dd>
        </div>
        <div>
          <dt className="text-sm text-graphite">Schedule</dt>
          <dd className="font-display text-2xl font-semibold">{fmtScheduleGap(a)}</dd>
        </div>
      </dl>
      {a.temporal_precision === "mixed" && (
        <p className="mt-2 text-sm text-graphite">Duke publishes only an in-service year, so schedules are compared by year.</p>
      )}

      <Heading>Why this pair matched</Heading>
      {o.evidence.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5">
          {o.evidence.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      ) : (
        <p className="text-graphite italic">The analysis returned no explanation for this pair.</p>
      )}

      <Heading>What they could coordinate</Heading>
      {resources.length > 0 ? (
        <ul>
          {resources.map((r) => (
            <li key={r.resource_id} className="flex items-center justify-between gap-3 border-b border-rule py-1.5 last:border-0">
              <span>
                {r.display_name}
                {r.evidence.length > 0 && <InfoTip text={r.evidence.join(" ")} />}
              </span>
              <PotentialPips level={r.potential} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-graphite italic">These project types share no resource categories.</p>
      )}
      <p className="mt-2 text-sm text-graphite">Areas worth a conversation, based on project type. Not a commitment or a savings estimate.</p>

      <Heading>Score breakdown</Heading>
      <div className="space-y-2">
        <Bar label="Geographic proximity" value={a.geographic_score} />
        <Bar label="Schedule" value={a.temporal_score} />
        <Bar label="Project description similarity" value={a.text_similarity_score} />
        <Bar label="Infrastructure similarity" value={a.infrastructure_similarity} />
      </div>

      <Heading>The two projects</Heading>
      <ProjectFacts p={o.project_a} />
      <ProjectFacts p={o.project_b} />

      <p className="mt-6 border-t border-rule pt-3 text-sm text-graphite">
        The score measures how strong a coordination opportunity looks in public planning data. It does not predict
        whether utilities will coordinate or how much they would save. Planners decide.
      </p>
    </article>
  );
}

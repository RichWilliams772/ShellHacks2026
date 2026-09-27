"use client";

import { useState } from "react";
import { runScenario } from "@/lib/api";
import type { Opportunity, Project, ScenarioOutcome } from "@/lib/types";

function knownStart(project: Project) {
  return /^\d{4}-\d{2}-\d{2}$/.test(project.start ?? "");
}

function yearOnly(project: Project) {
  return !knownStart(project) && project.date_precision === "year" && project.in_service_year != null;
}

function canShift(project: Project) {
  return knownStart(project) || yearOnly(project);
}

function scoreText(value: number | null) {
  return value == null ? "Not available" : String(value);
}

function changeText(value: number | null) {
  if (value == null) return "Not available";
  if (value > 0) return `+${value}`;
  return String(value);
}

function firstShiftable(opportunity: Opportunity) {
  const projects = [opportunity.project_a, opportunity.project_b];
  return projects.find((project) => knownStart(project))?.id
    ?? projects.find((project) => yearOnly(project))?.id
    ?? "";
}

export default function ScenarioPanel({ opportunity }: { opportunity: Opportunity }) {
  const projects = [opportunity.project_a, opportunity.project_b];
  const [projectId, setProjectId] = useState(() => firstShiftable(opportunity));
  const [shift, setShift] = useState("3");
  const [year, setYear] = useState("");
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState("");
  const [result, setResult] = useState<ScenarioOutcome | null>(null);

  const selected = projects.find((project) => project.id === projectId) ?? null;
  const usingYear = selected != null && yearOnly(selected);
  const shiftMonths = Number(shift);
  const shiftReady = shift.trim() !== "" && Number.isInteger(shiftMonths) && shiftMonths >= -36 && shiftMonths <= 36;
  const yearValue = Number(year);
  const yearReady = year.trim() !== "" && Number.isInteger(yearValue) && yearValue >= 1900 && yearValue <= 2200;

  function choose(project: Project) {
    setProjectId(project.id);
    if (yearOnly(project) && project.in_service_year != null) {
      setYear(String(project.in_service_year));
    }
  }

  async function apply() {
    if (!selected || !canShift(selected) || pending) return;
    if (usingYear && !yearReady) return;
    if (!usingYear && !shiftReady) return;
    setPending(true);
    setFailure("");
    try {
      const scenario = await runScenario(
        opportunity.opportunity_id,
        selected.id,
        usingYear ? { inServiceYear: yearValue } : { shiftMonths },
      );
      setResult(scenario);
    } catch (error) {
      setResult(null);
      setFailure(error instanceof Error ? error.message : "The scenario could not be calculated.");
    } finally {
      setPending(false);
    }
  }

  function reset() {
    const nextId = firstShiftable(opportunity);
    const next = projects.find((project) => project.id === nextId) ?? null;
    setShift("3");
    setYear(next && yearOnly(next) && next.in_service_year != null ? String(next.in_service_year) : "");
    setProjectId(nextId);
    setResult(null);
    setFailure("");
  }

  return (
    <section className="mt-6 border border-rule px-3 py-3" aria-label="What-If scenario">
      <h3 className="font-display text-xl font-semibold">What-If scenario</h3>
      <p className="mt-2 text-sm font-semibold">Hypothetical only; published project data was not changed.</p>
      <fieldset className="mt-3 space-y-2" disabled={pending}>
        <legend className="text-sm text-graphite">Project to shift</legend>
        {projects.map((project) => {
          const enabled = canShift(project);
          return (
            <label key={project.id} className="flex min-h-11 items-start gap-2 text-sm">
              <input
                type="radio"
                name={`scenario-project-${opportunity.opportunity_id}`}
                className="mt-1"
                checked={projectId === project.id}
                disabled={!enabled}
                onChange={() => choose(project)}
              />
              <span className="min-w-0 break-words">
                <span className="font-semibold">{project.utility}</span>
                <span className="block text-graphite">{project.name}</span>
                {knownStart(project) ? (
                  <span className="block">Published start {project.start}. End {project.end} stays fixed.</span>
                ) : yearOnly(project) ? (
                  <span className="block">
                    Year-only timing. Published in-service year {project.in_service_year}. No start date is invented.
                  </span>
                ) : (
                  <span className="block">
                    No known start date and no year-only in-service year. This choice stays off.
                  </span>
                )}
              </span>
            </label>
          );
        })}
      </fieldset>
      {usingYear ? (
        <label className="mt-3 block text-sm" htmlFor={`scenario-year-${opportunity.opportunity_id}`}>
          Hypothetical in-service year
          <input
            id={`scenario-year-${opportunity.opportunity_id}`}
            type="number"
            inputMode="numeric"
            min={1900}
            max={2200}
            step={1}
            value={year}
            onChange={(event) => setYear(event.target.value)}
            className="mt-1 min-h-11 w-full border border-rule bg-paper px-3 text-ink"
          />
        </label>
      ) : (
        <label className="mt-3 block text-sm" htmlFor={`scenario-shift-${opportunity.opportunity_id}`}>
          Start-date shift in months
          <input
            id={`scenario-shift-${opportunity.opportunity_id}`}
            type="number"
            inputMode="numeric"
            min={-36}
            max={36}
            step={1}
            value={shift}
            onChange={(event) => setShift(event.target.value)}
            className="mt-1 min-h-11 w-full border border-rule bg-paper px-3 text-ink"
          />
        </label>
      )}
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={() => void apply()}
          disabled={pending || !selected || !canShift(selected) || (usingYear ? !yearReady : !shiftReady)}
          className="min-h-11 rounded-full bg-cyan px-4 font-display font-semibold text-paper disabled:opacity-50"
        >
          {pending ? "Calculating…" : "Apply scenario"}
        </button>
        <button
          type="button"
          onClick={reset}
          className="min-h-11 rounded-full border border-rule px-4 font-display font-semibold"
        >
          Reset
        </button>
      </div>
      {usingYear && result?.dates.hypothetical_in_service_year == null && (
        <p className="mt-2 text-sm text-graphite">
          The published in-service year stays unchanged. A different year is a year-level estimate, not confirmed
          construction overlap.
        </p>
      )}
      {failure && (
        <p className="mt-3 text-sm" role="alert">
          {failure}
        </p>
      )}
      {result && (
        <div className="mt-4 space-y-2 break-words">
          <p className="font-display text-3xl font-semibold leading-tight">
            Current Score {scoreText(result.baseline_coordination_score)}
            <span className="mx-2 text-graphite">→</span>
            What-If Score {scoreText(result.scenario_coordination_score)}
          </p>
          <p className="text-sm">
            Temporal score {scoreText(result.baseline_temporal.temporal_score)} →{" "}
            {scoreText(result.scenario_temporal.temporal_score)} (change {changeText(result.temporal_score_change)})
          </p>
          {result.dates.hypothetical_in_service_year != null && <p className="text-sm">{result.assumption}</p>}
          <p className="text-sm text-graphite">{result.scenario_temporal.temporal_reason ?? result.explanation}</p>
          {result.score_unavailable_reason && <p className="text-sm">{result.score_unavailable_reason}</p>}
          {result.dates.scenario_start_date && (
            <p className="text-sm text-graphite">Hypothetical start {result.dates.scenario_start_date}.</p>
          )}
        </div>
      )}
    </section>
  );
}

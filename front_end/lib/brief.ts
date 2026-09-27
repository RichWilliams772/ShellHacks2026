// Formats an existing Opportunity into a plain-text brief a planner can paste into email,
// Slack, or meeting notes. Deterministic template only - reads fields already computed by
// the analysis pipeline, computes nothing, and never calls an LLM. A brief and the dashboard
// panel it came from must always agree, because they read the exact same object.
import type { Opportunity, Project } from "./types";

const NA_LINE = (label: string, reason: string) => `${label}: ${reason}`;

function locationLine(o: Opportunity): string {
  const { distance_miles } = o.analysis;
  if (distance_miles == null) return "Known endpoint distance: unavailable.";
  return `Approximately ${distance_miles.toFixed(1)} miles between known project endpoints.`;
}

// Mirrors the honesty rule already established for this field (Task 3/5): a year-level
// estimate is never presented as if it were a precise, verified overlap. Differentiates
// "same year" from "a few years apart" rather than calling every year-level pairing
// generically "compatible" - a pairing years apart should read as years apart, not glossed
// over, matching the same standard the dashboard itself already holds the score to.
function timingLine(o: Opportunity): string {
  const a = o.analysis;
  if (a.schedule_overlap_months != null) {
    return a.schedule_overlap_months > 0
      ? `Construction schedules overlap for approximately ${a.schedule_overlap_months} calendar months.`
      : "Available schedules show no calendar-month overlap.";
  }
  if (a.same_active_year) return "Both projects are estimated to be active in the same year.";
  if (a.year_difference != null) {
    return a.year_difference <= 1
      ? `Projects occur within a compatible planning period (about ${a.year_difference} year apart).`
      : `Projects' estimated timing differs by about ${a.year_difference} years.`;
  }
  return "Detailed schedule alignment is unavailable.";
}

function projectSources(p: Project): string[] {
  const s = p.sources;
  const values = [s.project_source, s.geography_source, s.circuit_endpoint_source, s.form1_schedule].filter(
    (v): v is string => Boolean(v),
  );
  return s.source_url ? [...values, s.source_url] : values;
}

// Only a question whose triggering condition is actually true for this opportunity - never a
// generic list, per the same "no invented completeness" rule the rest of GridSync follows.
function followUpQuestions(o: Opportunity): string[] {
  const a = o.analysis;
  const questions: string[] = [];

  if (a.schedule_overlap_months == null) {
    questions.push("Confirm the actual construction windows for both projects.");
  }
  // Specifically an "approximate_corridor" (a straight line between two known endpoints,
  // never the real route) - not just any known geometry. A "point" project is a single
  // substation with no corridor at all, so "routing beyond the known endpoints" doesn't
  // apply to it and shouldn't be asked about it.
  if (o.project_a.geometry_type === "approximate_corridor" || o.project_b.geometry_type === "approximate_corridor") {
    questions.push("Verify detailed project routing beyond the known endpoints.");
  }
  if (o.potential_shared_resources.length > 0) {
    questions.push(
      "Confirm whether the identified resource categories are operationally compatible and available during the relevant construction period.",
    );
  }
  if (a.score_confidence !== "HIGH") {
    questions.push("Review the underlying project data supporting this opportunity.");
  }
  if (o.project_a.voltage_label == null || o.project_b.voltage_label == null) {
    questions.push("Confirm missing infrastructure characteristics before coordination planning.");
  }
  return questions;
}

// One section = one heading plus its body lines (bullets are already "- " prefixed here so
// both renderers - plain text and the PDF - can just print them without re-deriving meaning).
export interface BriefSection {
  heading: string;
  lines: string[];
}

export interface Brief {
  title: string; // "<project A> x <project B>"
  score: string; // "63/100 (high confidence in the inputs)"
  sections: BriefSection[];
}

// The single source of truth for what a Coordination Brief says. formatCoordinationBrief()
// (plain text, for copy/paste) and lib/pdf.ts (the downloadable report) both render this same
// structure, so the two can never drift apart on what a brief actually claims.
export function buildBrief(o: Opportunity): Brief {
  const a = o.analysis;
  const sections: BriefSection[] = [
    { heading: "Location", lines: [locationLine(o)] },
    { heading: "Timing", lines: [timingLine(o)] },
    {
      heading: "Potential Coordination Areas",
      lines:
        o.potential_shared_resources.length > 0
          ? o.potential_shared_resources.map((r) => `- ${r.display_name} (${r.potential.toLowerCase()} potential)`)
          : ["No shared-resource categories were identified from the available project characteristics."],
    },
    {
      heading: "Data Confidence",
      lines: [a.score_confidence ? a.score_confidence : NA_LINE("Data confidence", "unavailable")],
    },
  ];

  const questions = followUpQuestions(o);
  if (questions.length > 0) sections.push({ heading: "Planner Follow-Up", lines: questions.map((q) => `- ${q}`) });

  const sources = [...new Set([...projectSources(o.project_a), ...projectSources(o.project_b)])];
  if (sources.length > 0) sections.push({ heading: "Sources", lines: sources.map((s) => `- ${s}`) });

  return {
    title: `${o.project_a.name} (${o.project_a.id}) x ${o.project_b.name} (${o.project_b.id})`,
    score: a.score_confidence
      ? `${Math.round(a.coordination_score)}/100 (${a.score_confidence.toLowerCase()} confidence in the inputs)`
      : `${Math.round(a.coordination_score)}/100`,
    sections,
  };
}

export function formatCoordinationBrief(o: Opportunity): string {
  const brief = buildBrief(o);
  const lines: string[] = [];

  lines.push("GridSync Coordination Brief", "");
  lines.push("Opportunity");
  lines.push(brief.title, "");
  lines.push("Coordination Score");
  lines.push(brief.score, "");

  for (const section of brief.sections) {
    lines.push(section.heading);
    lines.push(...section.lines);
    lines.push("");
  }

  lines.push("Generated by GridSync.");
  lines.push("Potential coordination opportunity for planner investigation.");

  return lines.join("\n");
}

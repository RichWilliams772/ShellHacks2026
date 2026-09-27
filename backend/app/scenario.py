"""Hypothetical timing changes for one selected opportunity.

The published project catalog is never written. Geographic, text-similarity, and
infrastructure scores are copied from the selected opportunity. Only an in-memory
start date or in-service year changes, and only Aaron's temporal and
coordination-score functions are called again.
"""

from __future__ import annotations

import calendar
import sys
from pathlib import Path
from typing import Any, TypeGuard

from app.errors import ScenarioRejected
from app.models import (
    Opportunity,
    Project,
    ScenarioDates,
    ScenarioOutcome,
    ScenarioTiming,
)

HYPOTHETICAL_NOTICE = "Hypothetical only; published project data was not changed."
END_DATE_ASSUMPTION = (
    "The original end date stays fixed. Only the hypothetical start date moves."
)
_DAY = 10


def run_scenario(
    opportunity: Opportunity,
    project_id: str,
    shift_months: int | None = None,
    in_service_year: int | None = None,
) -> ScenarioOutcome:
    if (shift_months is None) == (in_service_year is None):
        raise ScenarioRejected("Provide a start-date shift or a hypothetical in-service year.")
    selected = _project_on_pair(opportunity, project_id)
    if in_service_year is not None:
        shifted, dates, assumption = _year_shift(selected, in_service_year)
        applied_months = None
    else:
        assert shift_months is not None
        shifted, dates, assumption = _start_shift(selected, shift_months)
        applied_months = shift_months
    project_a = shifted if selected.id == opportunity.project_a.id else opportunity.project_a
    project_b = shifted if selected.id == opportunity.project_b.id else opportunity.project_b
    scenario_features = _temporal_features(_schedule_record(project_a), _schedule_record(project_b))
    components = opportunity.published_components
    geographic = None if components is None else components.geographic_score
    text_score = None if components is None else components.text_similarity_score
    infrastructure = None if components is None else components.infrastructure_similarity
    temporal_score = _number(scenario_features.get("temporal_score"))
    unavailable = _unavailable_reason(
        components is None,
        geographic,
        temporal_score,
        text_score,
        infrastructure,
    )
    scenario_score = None
    if unavailable is None:
        scenario_score = _coordination_score(geographic, temporal_score, text_score, infrastructure)
        if scenario_score is None:
            unavailable = (
                "A scenario coordination score was not calculated because the pair "
                "does not meet the published eligibility rules after this timing change."
            )
    baseline_score = opportunity.coordination_score
    baseline_temporal = _baseline_timing(opportunity)
    scenario_temporal = _scenario_timing(scenario_features)
    outcome = ScenarioOutcome(
        opportunity_id=opportunity.id,
        notice=HYPOTHETICAL_NOTICE,
        assumption=assumption,
        shift_months=applied_months,
        dates=dates,
        baseline_coordination_score=baseline_score,
        scenario_coordination_score=scenario_score,
        coordination_score_change=_change(baseline_score, scenario_score),
        baseline_temporal=baseline_temporal,
        scenario_temporal=scenario_temporal,
        temporal_score_change=_change(
            baseline_temporal.temporal_score,
            scenario_temporal.temporal_score,
        ),
        explanation="",
        limitations=_limitations(scenario_temporal, assumption),
        score_unavailable_reason=unavailable,
    )
    return outcome.model_copy(update={"explanation": _explanation(outcome)})


def _start_shift(selected: Project, shift_months: int) -> tuple[Project, ScenarioDates, str]:
    original_start = selected.start_date
    end_date = selected.end_date
    if not _full_date(original_start):
        raise ScenarioRejected(
            f"{selected.project_name} has no known start date. GridSync will not invent one."
        )
    if not _full_date(end_date):
        raise ScenarioRejected(
            f"{selected.project_name} has no known end date, so the start date cannot "
            "be shifted while keeping the end date fixed."
        )
    scenario_start = _add_months(original_start, shift_months)
    if scenario_start > end_date:
        raise ScenarioRejected(
            "The hypothetical start date is after the project's end date. "
            "The end date stays fixed, so this shift is not applied."
        )
    shifted = selected.model_copy(update={"start_date": scenario_start})
    dates = ScenarioDates(
        project_id=selected.id,
        project_name=selected.project_name,
        original_start_date=original_start,
        scenario_start_date=scenario_start,
        end_date=end_date,
    )
    return shifted, dates, END_DATE_ASSUMPTION


def _year_shift(selected: Project, in_service_year: int) -> tuple[Project, ScenarioDates, str]:
    if _full_date(selected.start_date):
        raise ScenarioRejected(
            f"{selected.project_name} has a known start date. "
            "Shift that start date instead of replacing the published year."
        )
    published = selected.estimated_in_service_year
    if selected.date_precision != "year" or published is None:
        raise ScenarioRejected(
            f"{selected.project_name} has no year-only in-service year. "
            "GridSync will not invent one."
        )
    shifted = selected.model_copy(update={"estimated_in_service_year": in_service_year})
    dates = ScenarioDates(
        project_id=selected.id,
        project_name=selected.project_name,
        published_in_service_year=published,
        hypothetical_in_service_year=in_service_year,
    )
    assumption = (
        f"The published in-service year stays {published}. "
        f"This estimate uses {in_service_year} for {selected.project_name}. "
        "It is a year-level estimate, not confirmed construction overlap."
    )
    return shifted, dates, assumption


def _project_on_pair(opportunity: Opportunity, project_id: str) -> Project:
    for project in (opportunity.project_a, opportunity.project_b):
        if project.id == project_id:
            return project
    raise ScenarioRejected(f"That project is not part of this opportunity: {project_id}")


def _full_date(value: str | None) -> TypeGuard[str]:
    if value is None or len(value) != _DAY:
        return False
    year, month, day = value.split("-")
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return False
    try:
        calendar.monthrange(int(year), int(month))
        return 1 <= int(day) <= calendar.monthrange(int(year), int(month))[1]
    except ValueError:
        return False


def _add_months(iso_date: str, months: int) -> str:
    year, month, day = (int(part) for part in iso_date.split("-"))
    index = month - 1 + months
    year += index // 12
    month = index % 12 + 1
    day = min(day, calendar.monthrange(year, month)[1])
    return f"{year:04d}-{month:02d}-{day:02d}"


def _schedule_record(project: Project) -> dict[str, object]:
    return {
        "start": project.start_date,
        "end": project.end_date,
        "in_service_year": project.estimated_in_service_year,
        "date_precision": project.date_precision,
    }


def _temporal_features(
    project_a: dict[str, object],
    project_b: dict[str, object],
) -> dict[str, Any]:
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from analysis.temporal import calculate_temporal_features

    features = calculate_temporal_features(project_a, project_b)
    if not isinstance(features, dict):
        raise ScenarioRejected("Timing could not be compared for this hypothetical start date.")
    return features


def _coordination_score(
    geographic: float | None,
    temporal: float | None,
    text_similarity: float | None,
    infrastructure: float | None,
) -> float | None:
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from analysis.scoring import calculate_coordination_score

    score = calculate_coordination_score(geographic, temporal, text_similarity, infrastructure)
    if score is None:
        return None
    return float(score)


def _unavailable_reason(
    missing_components: bool,
    geographic: float | None,
    temporal: float | None,
    text_similarity: float | None,
    infrastructure: float | None,
) -> str | None:
    if missing_components:
        return (
            "Published component scores are not available, so the scenario "
            "coordination score was not calculated."
        )
    if geographic is None:
        return (
            "A scenario coordination score was not calculated because the published "
            "geographic score is missing."
        )
    present = sum(
        value is not None
        for value in (geographic, temporal, text_similarity, infrastructure)
    )
    if present < 3:
        return (
            "A scenario coordination score was not calculated because fewer than "
            "three published components are available."
        )
    return None


def _baseline_timing(opportunity: Opportunity) -> ScenarioTiming:
    components = opportunity.published_components
    features = opportunity.features
    return ScenarioTiming(
        temporal_score=None if components is None else components.temporal_score,
        temporal_precision=features.temporal_precision,
        schedule_overlap_months=features.schedule_overlap_months,
        year_difference=features.year_difference,
        same_active_year=features.same_active_year,
        temporal_reason=None,
    )


def _scenario_timing(features: dict[str, Any]) -> ScenarioTiming:
    precision = features.get("temporal_precision")
    precision_text = precision if isinstance(precision, str) else None
    reason = features.get("temporal_reason")
    overlap = _number(features.get("schedule_overlap_months"))
    if precision_text != "month":
        overlap = None
    return ScenarioTiming(
        temporal_score=_number(features.get("temporal_score")),
        temporal_precision=precision_text,
        schedule_overlap_months=overlap,
        year_difference=_number(features.get("year_difference")),
        same_active_year=_flag(features.get("same_active_year")),
        temporal_reason=reason if isinstance(reason, str) else None,
    )


def _limitations(timing: ScenarioTiming, assumption: str) -> list[str]:
    limits = [
        HYPOTHETICAL_NOTICE,
        assumption,
        "Geographic, text-similarity, and infrastructure scores were copied from the "
        "published opportunity and were not recalculated.",
    ]
    if timing.temporal_precision != "month" or timing.schedule_overlap_months is None:
        limits.append(
            "schedule_overlap_months stays null. Same-year activity is not a "
            "confirmed month-level overlap. This is a year-level estimate, "
            "not confirmed construction overlap."
        )
    return limits


def _explanation(outcome: ScenarioOutcome) -> str:
    dates = outcome.dates
    if dates.hypothetical_in_service_year is not None:
        sentences = [outcome.assumption]
    else:
        months = outcome.shift_months if outcome.shift_months is not None else 0
        sentences = [
            (
                f"{dates.project_name} keeps the published end date {dates.end_date}. "
                f"The hypothetical start date moves from {dates.original_start_date} "
                f"to {dates.scenario_start_date} ({_signed(months)} months)."
            )
        ]
    if outcome.score_unavailable_reason:
        sentences.append(outcome.score_unavailable_reason)
    else:
        baseline = _fmt(outcome.baseline_coordination_score)
        scenario = _fmt(outcome.scenario_coordination_score)
        sentences.append(
            f"Current coordination score {baseline}. Scenario coordination score {scenario}."
        )
        change = outcome.coordination_score_change
        if change == 0:
            sentences.append("The coordination score is unchanged.")
        elif change is not None and change > 0:
            sentences.append(f"The coordination score is higher by {_fmt(change)}.")
        elif change is not None:
            sentences.append(f"The coordination score is lower by {_fmt(abs(change))}.")
    base_temporal = _fmt(outcome.baseline_temporal.temporal_score)
    scenario_temporal = _fmt(outcome.scenario_temporal.temporal_score)
    temporal_change = outcome.temporal_score_change
    if temporal_change == 0:
        sentences.append(f"The temporal score stays {base_temporal}.")
    else:
        sentences.append(
            f"The temporal score changes from {base_temporal} to {scenario_temporal}."
        )
    if outcome.scenario_temporal.temporal_reason:
        sentences.append(outcome.scenario_temporal.temporal_reason)
    if outcome.scenario_temporal.schedule_overlap_months is None:
        sentences.append("An exact schedule overlap in months is not confirmed.")
    if outcome.scenario_temporal.same_active_year is True:
        sentences.append("Sharing a calendar year is not a confirmed schedule overlap.")
    return " ".join(sentences)


def _change(baseline: float | None, scenario: float | None) -> float | None:
    if baseline is None or scenario is None:
        return None
    return round(scenario - baseline, 1)


def _fmt(value: float | None) -> str:
    if value is None:
        return "not available"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}"


def _signed(months: int) -> str:
    return f"+{months}" if months > 0 else str(months)


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _flag(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None

"""Map Aaron's precomputed analyze_projects() result onto the API opportunity model.

Processed mode calls ``analysis.pipeline.analyze_projects`` and copies score,
rank, evidence, and resource potential. It does not rerun geographic, temporal,
similarity, scoring, or resource calculations.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from app.config import SCORE_INTERPRETATION, Settings
from app.errors import LoaderError, OpportunityNotFoundError, SameUtilityError, UnknownUtilityError
from app.filters import OpportunityFilters
from app.models import (
    AnalyzeResponse,
    CoordinationPackage,
    CoordinationResource,
    DataConfidence,
    FeatureVector,
    Opportunity,
    Project,
    PublishedComponents,
    SharedResource,
)
from app.pairing import canonicalize_utility
from app.provenance import SOURCE_URL_GAP_NOTICE, labels_for

ENDPOINT_DISTANCE_LABEL = "minimum distance between known endpoints"
HIGH_OPPORTUNITY_NOTE = (
    "Prototype display threshold for counting higher-scoring opportunities. "
    "It is not a probability cutoff or a recommendation to coordinate."
)
PUBLIC_ANALYSIS_NOTICE = (
    "These opportunities are precomputed public Duke and TECO results. "
    "Coordination score, rank, evidence, and resource potential are copied "
    "from that analysis and were not recalculated here."
)
PUBLISHED_WEIGHTS = {
    "geographic": 0.40,
    "temporal": 0.30,
    "text_similarity": 0.20,
    "infrastructure": 0.10,
}
_PACKAGE_EVIDENCE = (
    "Potential shared resources are copied from the precomputed coordination package. "
    "potential is the published strength and was not recalculated here."
)
Precision = Literal["day", "month", "year", "mixed", "unknown", "unavailable"]
Strength = Literal["HIGH", "MEDIUM", "LOW"]


def analyze_processed(
    projects: list[Project],
    utility_a: str,
    utility_b: str,
    filters: OpportunityFilters,
    settings: Settings,
) -> AnalyzeResponse:
    resolved_a, resolved_b = _utilities(projects, utility_a, utility_b)
    by_id = {project.id: project for project in projects}
    payload = _analyze_projects()(resolved_a, resolved_b)
    summary = _mapping(payload.get("summary"))
    opportunities = [
        _opportunity(_mapping(item), by_id)
        for item in _records(payload.get("opportunities"))
    ]
    visible = [item for item in opportunities if _matches(item, filters)]
    visible.sort(key=_rank_key)
    high_count = sum(
        1
        for item in visible
        if item.coordination_score is not None
        and item.coordination_score >= settings.high_opportunity_minimum
    )
    pairs_evaluated = _whole(summary.get("pairs_analyzed")) or 0
    eligible = _whole(summary.get("eligible_opportunities")) or 0
    discarded = pairs_evaluated - eligible
    envelope = labels_for(project.data_type for project in projects)
    notice = f"{envelope.data_notice} {PUBLIC_ANALYSIS_NOTICE}"
    if any("source_url" in project.provenance_gaps for project in projects):
        notice = f"{notice} {SOURCE_URL_GAP_NOTICE}"
    return AnalyzeResponse(
        dataset_status=envelope.dataset_status,
        data_notice=notice,
        contains_demo_data=envelope.contains_demo_data,
        contains_verified_public_data=envelope.contains_verified_public_data,
        score_interpretation=SCORE_INTERPRETATION,
        utility_a=resolved_a,
        utility_b=resolved_b,
        projects_analyzed=_whole(summary.get("projects_analyzed")) or 0,
        pairs_evaluated=pairs_evaluated,
        pairs_discarded=discarded,
        discard_reasons={"coordination_score_ineligible": discarded},
        opportunity_count=len(visible),
        high_opportunity_count=high_count,
        high_opportunity_minimum=settings.high_opportunity_minimum,
        high_opportunity_note=HIGH_OPPORTUNITY_NOTE,
        weights=dict(PUBLISHED_WEIGHTS),
        thresholds={"high_opportunity_minimum": settings.high_opportunity_minimum},
        opportunities=visible,
    )


def get_processed_opportunity(
    projects: list[Project],
    opportunity_id: str,
    settings: Settings,
) -> Opportunity:
    resolved_a, resolved_b = _utilities(projects, "Duke Energy Florida", "Tampa Electric")
    analyzed = analyze_processed(
        projects,
        resolved_a,
        resolved_b,
        OpportunityFilters(),
        settings,
    )
    for opportunity in analyzed.opportunities:
        if opportunity.id == opportunity_id:
            return opportunity
    raise OpportunityNotFoundError(f"Opportunity not found: {opportunity_id}")


def _analyze_projects() -> Callable[..., dict[str, Any]]:
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from analysis.pipeline import analyze_projects

    return analyze_projects


def _utilities(projects: list[Project], utility_a: str, utility_b: str) -> tuple[str, str]:
    known = {project.utility for project in projects}
    resolved_a = _known_utility(utility_a, known)
    resolved_b = _known_utility(utility_b, known)
    if resolved_a.casefold() == resolved_b.casefold():
        raise SameUtilityError("GridSync only compares projects from different utilities.")
    return resolved_a, resolved_b


def _known_utility(name: str, known: set[str]) -> str:
    resolved = canonicalize_utility(name, known)
    if resolved in known:
        return resolved
    available = ", ".join(sorted(known)) or "none"
    raise UnknownUtilityError(f"Unknown utility: {resolved}. Loaded utilities: {available}.")


def _opportunity(row: dict[str, Any], projects: dict[str, Project]) -> Opportunity:
    opportunity_id = _text(row.get("opportunity_id"))
    if opportunity_id is None:
        raise LoaderError("Public opportunity is missing opportunity_id")
    project_a = _join(projects, _mapping(row.get("project_a")), opportunity_id, "project_a")
    project_b = _join(projects, _mapping(row.get("project_b")), opportunity_id, "project_b")
    analysis = _mapping(row.get("analysis"))
    precision = _precision(analysis.get("temporal_precision"), opportunity_id)
    overlap_months = _number(analysis.get("schedule_overlap_months"))
    if precision != "month" and overlap_months is not None:
        raise LoaderError(
            f"{opportunity_id}: temporal_precision {precision or 'blank'} "
            "cannot include exact schedule_overlap_months"
        )
    geographic_score = _number(analysis.get("geographic_score"))
    temporal_score = _number(analysis.get("temporal_score"))
    text_score = _number(analysis.get("text_similarity_score"))
    infrastructure_score = _number(analysis.get("infrastructure_similarity"))
    distance = _number(analysis.get("distance_miles"))
    evidence = [item for item in _texts(row.get("evidence")) if item]
    shared, resources = _resources(row.get("potential_shared_resources"), opportunity_id)
    data_type: Literal["public", "mixed"] = (
        "public" if project_a.data_type == "public" and project_b.data_type == "public" else "mixed"
    )
    return Opportunity(
        id=opportunity_id,
        project_a=project_a,
        project_b=project_b,
        features=FeatureVector(
            distance_miles=distance,
            distance_km=None,
            distance_method=None,
            distance_label=ENDPOINT_DISTANCE_LABEL,
            proximity_band=None,
            distance_similarity=None,
            temporal_precision=precision,
            start_date_difference=None,
            end_date_difference=None,
            start_year_difference=None,
            end_year_difference=None,
            overlap_days=None,
            schedule_overlap_months=overlap_months,
            overlap_years=None,
            overlapping_years=None,
            schedule_overlap_ratio=None,
            schedule_similarity=None,
            overlap_kind=None,
            year_difference=_number(analysis.get("year_difference")),
            same_active_year=_flag(analysis.get("same_active_year")),
            project_type_similarity=None,
            voltage_similarity=None,
            status_similarity=None,
            text_similarity=_unit_interval(text_score),
            cost_similarity=None,
            project_similarity=None,
            infrastructure_similarity=_unit_interval(infrastructure_score),
        ),
        features_used=_features_used(
            distance, geographic_score, temporal_score, text_score, infrastructure_score
        ),
        coordination_score=_number(analysis.get("coordination_score")),
        score_interpretation=SCORE_INTERPRETATION,
        base_weights=dict(PUBLISHED_WEIGHTS),
        effective_weights={},
        components=[],
        reasons=evidence,
        evidence_gaps=_gaps(project_a, project_b, temporal_score),
        coordination_package=CoordinationPackage(
            shared_resources=shared,
            resources=resources,
            evidence_note=_PACKAGE_EVIDENCE,
        ),
        data_type=data_type,
        coarse_filter_excluded=False,
        published_components=PublishedComponents(
            geographic_score=geographic_score,
            temporal_score=temporal_score,
            text_similarity_score=text_score,
            infrastructure_similarity=infrastructure_score,
            score_confidence=_text(analysis.get("score_confidence")),
            opportunity_rank=_whole(analysis.get("opportunity_rank")),
            geography_available=_flag(analysis.get("geography_available")),
        ),
        data_confidence=_confidence(_mapping(row.get("data_confidence"))),
    )


def _join(
    projects: dict[str, Project],
    view: dict[str, Any],
    opportunity_id: str,
    side: str,
) -> Project:
    project_id = _text(view.get("id"))
    if project_id is None:
        raise LoaderError(f"{opportunity_id} {side} is missing an id")
    project = projects.get(project_id)
    if project is None:
        raise LoaderError(f"{opportunity_id} references unknown {side} {project_id}")
    return project


def _resources(
    value: object,
    opportunity_id: str,
) -> tuple[list[SharedResource], list[CoordinationResource]]:
    shared: list[SharedResource] = []
    resources: list[CoordinationResource] = []
    for item in _records(value):
        resource_id = _text(item.get("resource_id"))
        label = _text(item.get("display_name")) or resource_id
        potential = _strength(_text(item.get("potential")), opportunity_id)
        if resource_id is None:
            raise LoaderError(f"{opportunity_id} resource is missing resource_id")
        evidence = _texts(item.get("evidence"))
        reason = evidence[0] if evidence else resource_id
        shared.append(
            SharedResource(
                resource=resource_id,
                label=label or resource_id,
                strength=potential,
                reason=reason,
            )
        )
        resources.append(
            CoordinationResource(
                name=resource_id,
                resource=resource_id,
                label=label or resource_id,
                strength=potential,
                potential=potential,
                reason=reason,
                evidence=evidence,
            )
        )
    return shared, resources


def _confidence(value: dict[str, Any]) -> DataConfidence:
    return DataConfidence(
        geography=_text(value.get("geography")),
        temporal=_text(value.get("temporal")),
        similarity=_text(value.get("similarity")),
        overall_score=_text(value.get("overall_score")),
    )


def _matches(opportunity: Opportunity, filters: OpportunityFilters) -> bool:
    if filters.year is not None:
        years = _schedule_years(opportunity.project_a) | _schedule_years(opportunity.project_b)
        if filters.year not in years:
            return False
    if filters.project_type:
        requested = filters.project_type.casefold()
        types = {
            opportunity.project_a.project_type.casefold()
            if opportunity.project_a.project_type
            else None,
            opportunity.project_b.project_type.casefold()
            if opportunity.project_b.project_type
            else None,
        }
        if requested not in types:
            return False
    if filters.max_distance_miles is not None:
        distance = opportunity.features.distance_miles
        if distance is None or distance > filters.max_distance_miles:
            return False
    if filters.min_coordination_score is not None:
        score = opportunity.coordination_score
        if score is None or score < filters.min_coordination_score:
            return False
    return True


def _schedule_years(project: Project) -> set[int]:
    years: set[int] = set()
    if project.estimated_in_service_year is not None:
        years.add(project.estimated_in_service_year)
    start = _calendar_year(project.start_date)
    end = _calendar_year(project.end_date)
    if start is not None and end is not None and start <= end <= start + 20:
        years.update(range(start, end + 1))
    else:
        if start is not None:
            years.add(start)
        if end is not None:
            years.add(end)
    return years


def _calendar_year(value: str | None) -> int | None:
    if value is None or len(value) < 4 or not value[:4].isdigit():
        return None
    return int(value[:4])


def _features_used(
    distance: float | None,
    geographic_score: float | None,
    temporal_score: float | None,
    text_score: float | None,
    infrastructure_score: float | None,
) -> list[str]:
    used: list[str] = []
    if distance is not None:
        used.append("distance_miles")
    if geographic_score is not None:
        used.append("geographic_score")
    if temporal_score is not None:
        used.append("temporal_score")
    if text_score is not None:
        used.append("text_similarity_score")
    if infrastructure_score is not None:
        used.append("infrastructure_similarity")
    return used


def _gaps(project_a: Project, project_b: Project, temporal_score: float | None) -> list[str]:
    gaps: list[str] = []
    for project in (project_a, project_b):
        if "source_url" in project.provenance_gaps:
            gaps.append(
                f"{project.id} has no source_url. source_name is the filing citation, not a URL."
            )
    if temporal_score is None:
        gaps.append("temporal_score is null because timing could not be compared.")
    return gaps


def _unit_interval(score_0_100: float | None) -> float | None:
    if score_0_100 is None:
        return None
    return score_0_100 / 100.0


def _precision(value: object, opportunity_id: str) -> Precision | None:
    text = _text(value)
    if text is None:
        return None
    if text == "day":
        return "day"
    if text == "month":
        return "month"
    if text == "year":
        return "year"
    if text == "mixed":
        return "mixed"
    if text == "unknown":
        return "unknown"
    if text == "unavailable":
        return "unavailable"
    raise LoaderError(f"{opportunity_id} temporal_precision {text} is not a known precision")


def _strength(value: str | None, opportunity_id: str) -> Strength:
    if value == "HIGH":
        return "HIGH"
    if value == "MEDIUM":
        return "MEDIUM"
    if value == "LOW":
        return "LOW"
    raise LoaderError(f"{opportunity_id} resource potential must be HIGH, MEDIUM, or LOW")


def _rank_key(opportunity: Opportunity) -> tuple[bool, int, str]:
    components = opportunity.published_components
    rank = None if components is None else components.opportunity_rank
    return (rank is None, rank or 0, opportunity.id)


def _records(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _texts(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    return None


def _whole(value: object) -> int | None:
    number = _number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _flag(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None

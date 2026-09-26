"""Assemble one cross-utility opportunity from the deterministic engines."""

from __future__ import annotations

from dataclasses import dataclass

from app.analysis_support import measured_features
from app.config import Settings
from app.geographic import compare_projects as compare_geography
from app.models import (
    CoordinationPackage,
    FeatureVector,
    Opportunity,
    Project,
    ScoreComponent,
    SharedResource,
)
from app.pairing import opportunity_id
from app.provenance import pair_data_type
from app.resources import CoordinationPackageResult, ResourceEvidence, coordination_package
from app.scoring import ScoreInputs, coordination_score
from app.similarity import compare_projects as compare_similarity
from app.temporal import compare_schedules

HIGH_OPPORTUNITY_NOTE = (
    "Prototype display threshold for counting higher-scoring opportunities. "
    "It is not a probability cutoff or a recommendation to coordinate."
)


@dataclass(frozen=True)
class OpportunityFilters:
    year: int | None = None
    project_type: str | None = None
    max_distance_miles: float | None = None
    min_coordination_score: float | None = None


def analyze_pair(project_a: Project, project_b: Project, settings: Settings) -> Opportunity:
    geography = compare_geography(project_a, project_b, settings)
    schedule = compare_schedules(project_a, project_b)
    similarity = compare_similarity(project_a, project_b, settings)
    score = coordination_score(
        ScoreInputs(
            distance_similarity=geography.distance_similarity,
            schedule_similarity=schedule.schedule_similarity,
            project_type_similarity=similarity.project_type_similarity,
            voltage_similarity=similarity.voltage_similarity,
            status_similarity=similarity.status_similarity,
            text_similarity=similarity.text_similarity,
        ),
        settings,
    )
    package = coordination_package(
        project_a.project_type,
        project_b.project_type,
        ResourceEvidence(
            project_type_similarity=similarity.project_type_similarity,
            distance_miles=geography.distance_miles,
            schedule_overlap_ratio=schedule.schedule_overlap_ratio,
            temporal_precision=schedule.precision,
        ),
        settings,
    )
    excluded = (
        geography.distance_miles is not None
        and geography.distance_miles > settings.max_pair_distance_miles
    )
    reasons = _unique(
        [
            *geography.reasons,
            *schedule.reasons,
            *similarity.reasons,
            *score.reasons,
        ]
    )
    gaps = _unique(
        [
            *geography.evidence_gaps,
            *schedule.evidence_gaps,
            *similarity.evidence_gaps,
            *score.evidence_gaps,
            *package.evidence_gaps,
        ]
    )
    return Opportunity(
        id=opportunity_id(project_a, project_b),
        project_a=project_a,
        project_b=project_b,
        features=FeatureVector(
            distance_miles=geography.distance_miles,
            distance_km=geography.distance_km,
            distance_method=geography.distance_method,
            proximity_band=geography.proximity_band,
            distance_similarity=geography.distance_similarity,
            temporal_precision=schedule.precision,
            start_date_difference=schedule.start_date_difference,
            end_date_difference=schedule.end_date_difference,
            start_year_difference=schedule.start_year_difference,
            end_year_difference=schedule.end_year_difference,
            overlap_days=schedule.overlap_days,
            schedule_overlap_months=schedule.schedule_overlap_months,
            overlap_years=schedule.overlap_years,
            overlapping_years=(
                None if schedule.overlapping_years is None else list(schedule.overlapping_years)
            ),
            schedule_overlap_ratio=schedule.schedule_overlap_ratio,
            schedule_similarity=schedule.schedule_similarity,
            overlap_kind=schedule.overlap_kind,
            project_type_similarity=similarity.project_type_similarity,
            voltage_similarity=similarity.voltage_similarity,
            status_similarity=similarity.status_similarity,
            text_similarity=similarity.text_similarity,
            cost_similarity=similarity.cost_similarity,
            project_similarity=score.project_similarity,
            infrastructure_similarity=score.infrastructure_similarity,
        ),
        features_used=measured_features(score.features_used, schedule.precision),
        coordination_score=score.coordination_score,
        score_interpretation=score.score_interpretation,
        base_weights=score.base_weights,
        effective_weights=score.effective_weights,
        components=[
            ScoreComponent(
                name=component.name,
                value=component.value,
                base_weight=component.base_weight,
                effective_weight=component.effective_weight,
                available=component.available,
            )
            for component in score.components
        ],
        reasons=reasons,
        evidence_gaps=gaps,
        coordination_package=_package_model(package),
        data_type=pair_data_type(project_a.data_type, project_b.data_type),
        coarse_filter_excluded=excluded,
    )


def _package_model(package: CoordinationPackageResult) -> CoordinationPackage:
    return CoordinationPackage(
        shared_resources=[
            SharedResource(
                resource=item.resource,
                label=item.label,
                strength=item.strength,
                reason=item.reason,
            )
            for item in package.shared_resources
        ],
        evidence_note=package.evidence_note,
    )


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered

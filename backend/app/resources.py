"""Deterministic shared-resource rules.

A resource is eligible only when it appears in the rule sets for both project
types. Strength counts how many configured evidence conditions are met.
The engine does not invent resources or savings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config import Settings
from app.similarity import normalize_label

RESOURCE_RULES: dict[str, tuple[str, ...]] = {
    "transmission_upgrade": (
        "specialized_line_crews",
        "heavy_equipment",
        "material_logistics",
        "outage_planning",
    ),
    "substation_upgrade": (
        "electrical_crews",
        "cranes",
        "transformer_logistics",
        "outage_planning",
    ),
    "undergrounding": (
        "excavation_crews",
        "trenching_equipment",
        "traffic_control",
        "material_logistics",
    ),
    "hardening": (
        "storm_restoration_crews",
        "heavy_equipment",
        "material_logistics",
        "outage_planning",
    ),
    "distribution_upgrade": (
        "distribution_crews",
        "material_logistics",
        "outage_planning",
    ),
}

TYPE_ALIASES: dict[str, str] = {
    "transmission_line": "transmission_upgrade",
    "reconductoring": "transmission_upgrade",
    "substation": "substation_upgrade",
    "storm_hardening": "hardening",
}

RESOURCE_LABELS: dict[str, str] = {
    "specialized_line_crews": "Specialized line crews",
    "heavy_equipment": "Heavy equipment",
    "material_logistics": "Material logistics",
    "outage_planning": "Outage planning",
    "electrical_crews": "Electrical crews",
    "cranes": "Cranes",
    "transformer_logistics": "Transformer logistics",
    "excavation_crews": "Excavation crews",
    "trenching_equipment": "Trenching equipment",
    "traffic_control": "Traffic control",
    "storm_restoration_crews": "Storm restoration crews",
    "distribution_crews": "Distribution crews",
}

Strength = Literal["HIGH", "MEDIUM", "LOW"]
_PACKAGE_NOTE = (
    "Potential shared resources are the intersection of deterministic project-type rules. "
    "Strength counts project-type similarity, distance, and schedule overlap against "
    "configured thresholds. This is not a recommendation and it does not estimate savings."
)


@dataclass(frozen=True)
class ResourceEvidence:
    project_type_similarity: float | None
    distance_miles: float | None
    schedule_overlap_ratio: float | None
    temporal_precision: str


@dataclass(frozen=True)
class SharedResourceResult:
    resource: str
    label: str
    strength: Strength
    reason: str


@dataclass(frozen=True)
class CoordinationPackageResult:
    shared_resources: tuple[SharedResourceResult, ...]
    evidence_note: str
    evidence_gaps: tuple[str, ...]


def canonical_project_type(project_type: str | None) -> str | None:
    normalized = normalize_label(project_type)
    if normalized is None:
        return None
    return TYPE_ALIASES.get(normalized, normalized)


def resources_for_type(project_type: str | None) -> tuple[str, ...]:
    canonical = canonical_project_type(project_type)
    if canonical is None:
        return ()
    return RESOURCE_RULES.get(canonical, ())


def shared_resource_names(type_a: str | None, type_b: str | None) -> tuple[str, ...]:
    shared = set(resources_for_type(type_a)) & set(resources_for_type(type_b))
    return tuple(sorted(shared))


def coordination_package(
    type_a: str | None,
    type_b: str | None,
    evidence: ResourceEvidence,
    settings: Settings,
) -> CoordinationPackageResult:
    gaps: list[str] = []
    for label, project_type in (("project A", type_a), ("project B", type_b)):
        if project_type is None:
            gaps.append(
                f"{label} has no project type, so its resource rules were not applied."
            )
        elif not resources_for_type(project_type):
            gaps.append(
                f"No resource rule is configured for project type {normalize_label(project_type)}."
            )
    names = shared_resource_names(type_a, type_b)
    if not names:
        return CoordinationPackageResult(
            shared_resources=(),
            evidence_note=(
                "No shared resources were identified. The deterministic rule tables for "
                "these project types do not intersect, or a project type has no rule."
            ),
            evidence_gaps=tuple(gaps),
        )
    strength, reason = _strength(evidence, settings)
    resources = tuple(
        SharedResourceResult(
            resource=name,
            label=RESOURCE_LABELS.get(name, name.replace("_", " ").capitalize()),
            strength=strength,
            reason=reason,
        )
        for name in names
    )
    return CoordinationPackageResult(
        shared_resources=resources,
        evidence_note=_PACKAGE_NOTE,
        evidence_gaps=tuple(gaps),
    )


def _strength(evidence: ResourceEvidence, settings: Settings) -> tuple[Strength, str]:
    type_met = (
        evidence.project_type_similarity is not None
        and evidence.project_type_similarity >= settings.resource_type_similarity_min
    )
    distance_met = (
        evidence.distance_miles is not None
        and evidence.distance_miles < settings.resource_high_distance_miles
    )
    overlap_met = (
        evidence.schedule_overlap_ratio is not None
        and evidence.schedule_overlap_ratio >= settings.resource_meaningful_overlap_ratio
    )
    met_count = sum((type_met, distance_met, overlap_met))
    if met_count >= 3:
        strength: Strength = "HIGH"
    elif met_count == 2:
        strength = "MEDIUM"
    else:
        strength = "LOW"
    type_text = _condition(
        "project-type similarity",
        type_met,
        _number(evidence.project_type_similarity),
        f"at least {settings.resource_type_similarity_min:.2f}",
    )
    distance_text = _condition(
        "distance",
        distance_met,
        _miles(evidence.distance_miles),
        f"under {settings.resource_high_distance_miles:.0f} miles",
    )
    if evidence.temporal_precision == "year":
        overlap_label = "year-level schedule overlap ratio"
    elif evidence.temporal_precision == "day":
        overlap_label = "schedule overlap ratio"
    else:
        overlap_label = "schedule overlap"
    overlap_text = _condition(
        overlap_label,
        overlap_met,
        _number(evidence.schedule_overlap_ratio),
        f"at least {settings.resource_meaningful_overlap_ratio:.2f}",
    )
    reason = (
        f"Strength is {strength} because {met_count} of 3 conditions were met. "
        f"{type_text} {distance_text} {overlap_text}"
    )
    return strength, reason


def _condition(label: str, met: bool, observed: str, requirement: str) -> str:
    state = "Met" if met else "Unmet"
    return f"{state}: {label} is {observed} ({requirement})."


def _number(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.2f}"


def _miles(value: float | None) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.1f} miles"

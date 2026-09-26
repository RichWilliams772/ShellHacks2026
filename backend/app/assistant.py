"""Structured retrieval assistant.

The assistant filters and explains opportunities that the analysis engine
already computed. It does not calculate distance, overlap, scores, resource
eligibility, sources, or savings.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

from app.config import SCORE_INTERPRETATION
from app.models import Opportunity, Project
from app.similarity import type_matches

_SAVINGS_PATTERN = re.compile(
    r"\b(savings|roi|probability|recommend|should we coordinate|financial)\b",
    re.IGNORECASE,
)
_BEFORE_YEAR = re.compile(r"\bbefore\s+(20\d{2})\b", re.IGNORECASE)
_IN_YEAR = re.compile(r"\bin\s+(20\d{2})\b", re.IGNORECASE)
_WITHIN_MILES = re.compile(r"\bwithin\s+(\d+(?:\.\d+)?)\s+miles\b", re.IGNORECASE)
_ASSISTANT_NOTE = (
    "Numerical features, resource eligibility, sources, and scores in this answer "
    "were copied from GridSync analysis results. The assistant did not calculate them."
)


@dataclass(frozen=True)
class AssistantResult:
    answer: str
    note: str
    filters_applied: dict[str, object]
    opportunities: list[Opportunity]
    llm_used: bool
    llm_configured: bool


def llm_is_configured(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return bool(env.get("GRIDSYNC_LLM_API_KEY", "").strip())


def answer_query(
    query: str,
    opportunities: list[Opportunity],
    *,
    llm_configured: bool | None = None,
) -> AssistantResult:
    configured = llm_is_configured() if llm_configured is None else llm_configured
    if _SAVINGS_PATTERN.search(query):
        return AssistantResult(
            answer=(
                "GridSync does not calculate savings, probability, financial ROI, or a "
                "recommendation to coordinate. The coordination score only measures "
                "opportunity strength from the structured analysis."
            ),
            note=_ASSISTANT_NOTE,
            filters_applied={"unsupported": "savings_or_recommendation"},
            opportunities=[],
            llm_used=False,
            llm_configured=configured,
        )
    filters = _filters_from_query(query)
    matched = [item for item in opportunities if _matches_query(item, filters)]
    if filters.limit is not None:
        matched = matched[: filters.limit]
    answer = _explain(query, matched, filters, configured)
    return AssistantResult(
        answer=answer,
        note=_ASSISTANT_NOTE,
        filters_applied=filters.as_dict(),
        opportunities=matched,
        llm_used=False,
        llm_configured=configured,
    )


@dataclass(frozen=True)
class _QueryFilters:
    year: int | None = None
    before_year: int | None = None
    max_distance_miles: float | None = None
    project_type: str | None = None
    limit: int | None = None
    include_reasons: bool = False
    include_resources: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "year": self.year,
            "before_year": self.before_year,
            "max_distance_miles": self.max_distance_miles,
            "project_type": self.project_type,
            "limit": self.limit,
            "include_reasons": self.include_reasons,
            "include_resources": self.include_resources,
        }


def _filters_from_query(query: str) -> _QueryFilters:
    lowered = query.casefold()
    year_match = _IN_YEAR.search(query)
    before_match = _BEFORE_YEAR.search(query)
    miles_match = _WITHIN_MILES.search(query)
    if "transmission upgrade" in lowered:
        project_type = "transmission_upgrade"
    elif "substation" in lowered:
        project_type = "substation"
    elif "underground" in lowered:
        project_type = "undergrounding"
    elif "transmission" in lowered:
        project_type = "transmission"
    else:
        project_type = None
    limit = 5 if "strongest" in lowered or "top" in lowered else None
    return _QueryFilters(
        year=int(year_match.group(1)) if year_match else None,
        before_year=int(before_match.group(1)) if before_match else None,
        max_distance_miles=float(miles_match.group(1)) if miles_match else None,
        project_type=project_type,
        limit=limit,
        include_reasons="why" in lowered,
        include_resources=any(word in lowered for word in ("resource", "crew", "equipment")),
    )


def _matches_query(opportunity: Opportunity, filters: _QueryFilters) -> bool:
    if filters.year is not None:
        years = opportunity.features.overlapping_years
        if years is None or filters.year not in years:
            return False
    if filters.max_distance_miles is not None:
        distance = opportunity.features.distance_miles
        if distance is None or distance > filters.max_distance_miles:
            return False
    if filters.project_type is not None and not _type_requested(opportunity, filters.project_type):
        return False
    if filters.before_year is not None:
        if not _ends_before(opportunity.project_a, filters.before_year):
            return False
        if not _ends_before(opportunity.project_b, filters.before_year):
            return False
    return True


def _type_requested(opportunity: Opportunity, requested: str) -> bool:
    return type_matches(opportunity.project_a.project_type, requested) or type_matches(
        opportunity.project_b.project_type, requested
    )


def _ends_before(project: Project, year: int) -> bool:
    if project.end_date is None or len(project.end_date) < 4 or not project.end_date[:4].isdigit():
        return False
    return int(project.end_date[:4]) < year


def _explain(
    query: str,
    opportunities: list[Opportunity],
    filters: _QueryFilters,
    llm_configured: bool,
) -> str:
    lines = [
        "This answer uses structured GridSync results only. No distances, schedule "
        "overlaps, scores, resources, or sources were recalculated.",
    ]
    if llm_configured:
        lines.append(
            "GRIDSYNC_LLM_API_KEY is set, but this endpoint still returns structured "
            "retrieval. The model is not asked to calculate or replace evidence."
        )
    if not opportunities:
        lines.append(f"No opportunities matched: {query.strip()}")
        lines.append(SCORE_INTERPRETATION)
        return " ".join(lines)
    lines.append(f"{len(opportunities)} opportunities matched.")
    for opportunity in opportunities[:5]:
        lines.append(
            f"{opportunity.id} has coordination score {opportunity.coordination_score} "
            f"and data_type {opportunity.data_type}."
        )
        if filters.include_reasons or filters.limit is not None:
            lines.extend(opportunity.reasons)
        if filters.include_resources:
            resources = opportunity.coordination_package.shared_resources
            if not resources:
                lines.append(opportunity.coordination_package.evidence_note)
            else:
                for resource in resources:
                    lines.append(f"{resource.label} {resource.strength}. {resource.reason}")
        if opportunity.evidence_gaps and filters.include_reasons:
            lines.append("Evidence gaps: " + " ".join(opportunity.evidence_gaps))
    lines.append(opportunities[0].score_interpretation)
    return " ".join(lines)

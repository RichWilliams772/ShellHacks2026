"""In-memory catalog and opportunity queries."""

from __future__ import annotations

from collections import Counter

from app.analysis import HIGH_OPPORTUNITY_NOTE, analyze_pair
from app.config import SCORE_INTERPRETATION, Settings
from app.errors import OpportunityNotFoundError, ProjectNotFoundError, UnknownUtilityError
from app.filters import OpportunityFilters
from app.fixtures import DUKE, TECO
from app.models import AnalyzeResponse, Opportunity, Project, UtilitySummary
from app.pairing import canonicalize_utility, generate_cross_pairs, parse_opportunity_id
from app.provenance import (
    DEMO_ANALYSIS_ISOLATED_NOTICE,
    SOURCE_URL_GAP_NOTICE,
    DataLabels,
    labels_for,
)
from app.similarity import type_matches
from app.temporal import active_years


class AnalysisService:
    def __init__(
        self,
        projects: list[Project],
        settings: Settings,
        analysis_projects: list[Project] | None = None,
    ) -> None:
        self.projects = list(projects)
        if analysis_projects is None:
            self.analysis_projects = list(self.projects)
        else:
            self.analysis_projects = list(analysis_projects)
        self.settings = settings
        self.analysis_isolated = analysis_projects is not None
        self.by_id = {project.id: project for project in self.projects}
        self.analysis_by_id = {project.id: project for project in self.analysis_projects}
        if len(self.by_id) != len(self.projects):
            raise ValueError("Project ids must be unique")
        if len(self.analysis_by_id) != len(self.analysis_projects):
            raise ValueError("Analysis project ids must be unique")

    def envelope(self) -> DataLabels:
        labels = labels_for(project.data_type for project in self.projects)
        if any("source_url" in project.provenance_gaps for project in self.projects):
            return labels._replace(data_notice=f"{labels.data_notice} {SOURCE_URL_GAP_NOTICE}")
        return labels

    def analysis_envelope(self) -> DataLabels:
        labels = labels_for(project.data_type for project in self.analysis_projects)
        if self.analysis_isolated:
            return labels._replace(
                data_notice=f"{labels.data_notice} {DEMO_ANALYSIS_ISOLATED_NOTICE}"
            )
        return labels

    def list_utilities(self) -> list[UtilitySummary]:
        counts: Counter[str] = Counter(project.utility for project in self.projects)
        summaries: list[UtilitySummary] = []
        for name in sorted(counts):
            data_types: list[str] = []
            demo_rows = [
                project
                for project in self.projects
                if project.utility == name and project.data_type == "demo"
            ]
            public_rows = [
                project
                for project in self.projects
                if project.utility == name and project.data_type == "public"
            ]
            if demo_rows:
                data_types.append("demo")
            if public_rows:
                data_types.append("public")
            summaries.append(
                UtilitySummary.model_validate(
                    {
                        "name": name,
                        "project_count": counts[name],
                        "data_types": data_types,
                    }
                )
            )
        return summaries

    def list_projects(
        self,
        *,
        utility: str | None = None,
        project_type: str | None = None,
        year: int | None = None,
    ) -> list[Project]:
        known = {project.utility for project in self.projects}
        selected_utility = canonicalize_utility(utility, known) if utility else None
        matched: list[Project] = []
        for project in self.projects:
            if selected_utility is not None and project.utility != selected_utility:
                continue
            if project_type and not type_matches(project.project_type, project_type):
                continue
            if year is not None:
                years = active_years(project)
                if years is None or year not in years:
                    continue
            matched.append(project)
        return sorted(matched, key=lambda project: (project.utility, project.id))

    def get_project(self, project_id: str) -> Project:
        project = self.by_id.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return project

    def analyze(
        self,
        utility_a: str,
        utility_b: str,
        filters: OpportunityFilters,
    ) -> AnalyzeResponse:
        if self.settings.project_catalog == "processed":
            from app.public_analysis import analyze_processed

            return analyze_processed(
                self.projects, utility_a, utility_b, filters, self.settings
            )
        pairs = generate_cross_pairs(self.analysis_projects, utility_a, utility_b)
        known = {project.utility for project in self.analysis_projects}
        resolved_a = canonicalize_utility(utility_a, known)
        resolved_b = canonicalize_utility(utility_b, known)
        discarded = 0
        retained: list[Opportunity] = []
        for project_a, project_b in pairs:
            opportunity = analyze_pair(project_a, project_b, self.settings)
            if opportunity.coarse_filter_excluded:
                discarded += 1
                continue
            retained.append(opportunity)
        visible = [item for item in retained if opportunity_matches(item, filters)]
        visible.sort(key=_sort_key)
        high_count = sum(
            1
            for item in visible
            if item.coordination_score is not None
            and item.coordination_score >= self.settings.high_opportunity_minimum
        )
        envelope = self.analysis_envelope()
        return AnalyzeResponse(
            dataset_status=envelope.dataset_status,
            data_notice=envelope.data_notice,
            contains_demo_data=envelope.contains_demo_data,
            contains_verified_public_data=envelope.contains_verified_public_data,
            score_interpretation=SCORE_INTERPRETATION,
            utility_a=resolved_a,
            utility_b=resolved_b,
            projects_analyzed=len({project.id for pair in pairs for project in pair}),
            pairs_evaluated=len(pairs),
            pairs_discarded=discarded,
            discard_reasons={"beyond_max_distance": discarded},
            opportunity_count=len(visible),
            high_opportunity_count=high_count,
            high_opportunity_minimum=self.settings.high_opportunity_minimum,
            high_opportunity_note=HIGH_OPPORTUNITY_NOTE,
            weights=self.settings.public_weights(),
            thresholds=self.settings.public_thresholds(),
            opportunities=visible,
        )

    def get_opportunity(self, opportunity_id_value: str) -> Opportunity:
        if self.settings.project_catalog == "processed":
            from app.public_analysis import get_processed_opportunity

            return get_processed_opportunity(
                self.projects, opportunity_id_value, self.settings
            )
        try:
            left_id, right_id = parse_opportunity_id(opportunity_id_value)
        except ValueError as exc:
            raise OpportunityNotFoundError(
                f"Opportunity not found: {opportunity_id_value}"
            ) from exc
        left = self.analysis_by_id.get(left_id)
        right = self.analysis_by_id.get(right_id)
        if left is None or right is None or left.utility == right.utility:
            raise OpportunityNotFoundError(f"Opportunity not found: {opportunity_id_value}")
        opportunity = analyze_pair(left, right, self.settings)
        if opportunity.id != opportunity_id_value:
            raise OpportunityNotFoundError(f"Opportunity not found: {opportunity_id_value}")
        return opportunity

    def default_utilities(self) -> tuple[str, str]:
        known = {project.utility for project in self.analysis_projects}
        if DUKE in known and TECO in known:
            return DUKE, TECO
        names = sorted(known)
        if len(names) < 2:
            raise UnknownUtilityError(
                "At least two utilities are required to build opportunities."
            )
        return names[0], names[1]


def opportunity_matches(opportunity: Opportunity, filters: OpportunityFilters) -> bool:
    if filters.year is not None:
        years = opportunity.features.overlapping_years
        if years is None or filters.year not in years:
            return False
    if filters.project_type:
        if not (
            type_matches(opportunity.project_a.project_type, filters.project_type)
            or type_matches(opportunity.project_b.project_type, filters.project_type)
        ):
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


def _sort_key(opportunity: Opportunity) -> tuple[bool, float, str]:
    score = opportunity.coordination_score
    missing_score = score is None
    return (missing_score, -(score or 0.0), opportunity.id)

"""Join Aaron's pair-similarity CSV to the processed Duke and TECO catalogs.

Call ``PairComparisonAdapter(projects).load()``.

``projects`` is the catalog from ``ProcessedProjectLoader.load_projects()``.
``path`` overrides ``data/processed/duke_teco_pair_similarity.csv``. That file
keeps every geographic and temporal column and adds text and infrastructure
similarity. This module copies those values. It does not refit text similarity,
rescore infrastructure, blend components, or build shared resources.

``text_similarity_raw`` stays on a 0 to 1 scale. ``text_similarity_score``,
``project_type_similarity``, ``voltage_similarity``, and
``infrastructure_similarity`` stay on Aaron's 0 to 100 scale.
``coordination_score`` and ``shared_resources`` stay null.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.errors import LoaderError
from app.models import Project
from app.processed_loader import _number, _read_csv, _text, processed_directory

PAIR_SIMILARITY_FILENAME = "duke_teco_pair_similarity.csv"
UNIT_INTERVAL: Literal["0_to_1"] = "0_to_1"
SCORE_0_TO_100: Literal["0_to_100"] = "0_to_100"
SIMILARITY_SCALE_NOTE = (
    "text_similarity_raw is cosine similarity on a 0 to 1 scale. "
    "text_similarity_score, project_type_similarity, voltage_similarity, and "
    "infrastructure_similarity are Aaron's 0 to 100 scores. They are copied as "
    "published and are not blended."
)
SIMILARITY_CONFIDENCE_NOTE = (
    "similarity_confidence describes how much similarity evidence is present. "
    "It is not a similarity strength."
)
ENDPOINT_DISTANCE_NOTE = (
    "minimum_endpoint_distance_miles is the smallest distance among known project "
    "endpoints. It is not the distance between transmission routes."
)
OVERLAP_MONTHS_NOTE = (
    "schedule_overlap_months is set only when temporal_precision is month. "
    "A mixed or year comparison keeps year_difference and does not report exact overlap months."
)
PARTIAL_COMPARISON_STATUS: Literal["partial_public_features"] = "partial_public_features"

PAIR_FEATURE_COLUMNS = (
    "pair_id",
    "project_a_id",
    "project_b_id",
    "project_a_utility",
    "project_b_utility",
    "project_a_location_confidence",
    "project_b_location_confidence",
    "geography_available_both",
    "geography_available",
    "geography_point_count_a",
    "geography_point_count_b",
    "minimum_endpoint_distance_miles",
    "project_a_nearest_endpoint",
    "project_b_nearest_endpoint",
    "pair_geography_confidence",
    "geographic_score",
    "geographic_reason",
    "temporal_data_available",
    "temporal_precision",
    "schedule_overlap",
    "schedule_overlap_months",
    "same_active_year",
    "year_difference",
    "temporal_score",
    "temporal_reason",
    "text_similarity_available",
    "text_similarity_raw",
    "text_similarity_score",
    "shared_text_terms",
    "project_type_similarity",
    "voltage_similarity",
    "infrastructure_similarity_available",
    "infrastructure_similarity",
    "similarity_confidence",
)


class EndpointGeography(BaseModel):
    """Endpoint proximity copied from the pair file. Scores are not recomputed."""

    model_config = ConfigDict(extra="forbid")

    geography_available: bool | None
    geography_available_both: bool | None
    geography_point_count_a: int | None
    geography_point_count_b: int | None
    minimum_endpoint_distance_miles: float | None
    distance_kind: Literal["known_endpoints"] = "known_endpoints"
    route_distance_miles: None = None
    distance_note: str = ENDPOINT_DISTANCE_NOTE
    project_a_nearest_endpoint: str | None = None
    project_b_nearest_endpoint: str | None = None
    project_a_location_confidence: str | None = None
    project_b_location_confidence: str | None = None
    pair_geography_confidence: str | None = None
    geographic_score: float | None = None
    geographic_reason: str | None = None

    @model_validator(mode="after")
    def _unmeasured_geography_stays_null(self) -> EndpointGeography:
        if self.geography_available is False and (
            self.minimum_endpoint_distance_miles is not None or self.geographic_score is not None
        ):
            raise ValueError(
                "unmeasured geography must keep minimum_endpoint_distance_miles "
                "and geographic_score null"
            )
        return self


class TemporalFeatures(BaseModel):
    """Timing features copied from the pair file. Year gaps are not overlap months."""

    model_config = ConfigDict(extra="forbid")

    temporal_data_available: bool | None
    temporal_precision: Literal["month", "year", "mixed", "unknown"] | None
    schedule_overlap: bool | None = None
    schedule_overlap_months: float | None = None
    schedule_overlap_months_are_exact: bool
    same_active_year: bool | None = None
    year_difference: int | None = None
    temporal_score: float | None = None
    temporal_reason: str | None = None
    overlap_note: str = OVERLAP_MONTHS_NOTE

    @model_validator(mode="after")
    def _overlap_months_follow_precision(self) -> TemporalFeatures:
        month_level = self.temporal_precision == "month"
        if self.schedule_overlap_months_are_exact is not month_level:
            raise ValueError("schedule_overlap_months_are_exact is true only at month precision")
        if not month_level and (
            self.schedule_overlap is not None or self.schedule_overlap_months is not None
        ):
            raise ValueError(
                "mixed, year, and unknown comparisons cannot carry exact overlap months"
            )
        if self.temporal_data_available is False and self.temporal_score is not None:
            raise ValueError("unavailable timing must keep temporal_score null")
        return self


class SimilarityFeatures(BaseModel):
    """Text and infrastructure similarity copied from the pair file."""

    model_config = ConfigDict(extra="forbid")

    text_similarity_available: bool | None
    text_similarity_raw: float | None = None
    text_similarity_raw_scale: Literal["0_to_1"] = UNIT_INTERVAL
    text_similarity_score: float | None = None
    text_similarity_score_scale: Literal["0_to_100"] = SCORE_0_TO_100
    shared_text_terms_raw: str | None = None
    shared_text_terms: list[str] = Field(default_factory=list)
    project_type_similarity: float | None = None
    project_type_similarity_scale: Literal["0_to_100"] = SCORE_0_TO_100
    voltage_similarity: float | None = None
    voltage_similarity_scale: Literal["0_to_100"] = SCORE_0_TO_100
    infrastructure_similarity_available: bool | None
    infrastructure_similarity: float | None = None
    infrastructure_similarity_scale: Literal["0_to_100"] = SCORE_0_TO_100
    similarity_confidence: str | None = None
    scale_note: str = SIMILARITY_SCALE_NOTE
    similarity_confidence_note: str = SIMILARITY_CONFIDENCE_NOTE

    @model_validator(mode="after")
    def _unavailable_similarity_stays_null(self) -> SimilarityFeatures:
        text_missing = self.text_similarity_available is False
        text_filled = self.text_similarity_raw is not None or self.text_similarity_score is not None
        if text_missing and text_filled:
            raise ValueError("unavailable text similarity must keep raw and score null")
        infrastructure_missing = self.infrastructure_similarity_available is False
        if infrastructure_missing and self.infrastructure_similarity is not None:
            raise ValueError("unavailable infrastructure similarity must stay null")
        return self


class PairComparison(BaseModel):
    """One joined Duke–TECO pair. This is not a completed opportunity."""

    model_config = ConfigDict(extra="forbid")

    pair_id: str
    project_a: Project
    project_b: Project
    geography: EndpointGeography
    temporal: TemporalFeatures
    similarity: SimilarityFeatures
    comparison_status: Literal["partial_public_features"] = PARTIAL_COMPARISON_STATUS
    coordination_score: None = None
    shared_resources: None = None
    features_complete: Literal[False] = False

    @model_validator(mode="after")
    def _two_utilities(self) -> PairComparison:
        same_project = self.project_a.id == self.project_b.id
        same_utility = self.project_a.utility == self.project_b.utility
        if same_project or same_utility:
            raise ValueError("a comparison must reference two projects from different utilities")
        return self


class PairComparisonAdapter:
    """Load pair-feature rows and join them to an existing project catalog."""

    def __init__(
        self,
        projects: list[Project],
        path: str | Path | None = None,
    ) -> None:
        self.projects = list(projects)
        self.by_id = {project.id: project for project in self.projects}
        if len(self.by_id) != len(self.projects):
            raise LoaderError("Project ids must be unique")
        directory = processed_directory()
        self.path = Path(path) if path else directory / PAIR_SIMILARITY_FILENAME

    def load(self) -> list[PairComparison]:
        rows, columns = _read_csv(self.path)
        missing = [column for column in PAIR_FEATURE_COLUMNS if column not in columns]
        if missing:
            raise LoaderError(
                f"{self.path.name} is missing pair-feature columns: {', '.join(missing)}"
            )
        comparisons: list[PairComparison] = []
        seen: set[str] = set()
        for row_number, row in enumerate(rows, start=1):
            comparison = _map_row(row, self.by_id, row_number, self.path.name)
            if comparison.pair_id in seen:
                raise LoaderError(f"{self.path.name} row {row_number}: duplicate pair_id")
            seen.add(comparison.pair_id)
            comparisons.append(comparison)
        return comparisons


def _map_row(
    row: dict[str, str],
    projects: dict[str, Project],
    row_number: int,
    filename: str,
) -> PairComparison:
    pair_id = _required_text(row, "pair_id", row_number, filename)
    project_a_id = _required_text(row, "project_a_id", row_number, filename)
    project_b_id = _required_text(row, "project_b_id", row_number, filename)
    if pair_id != f"{project_a_id}__{project_b_id}":
        raise LoaderError(
            f"{filename} row {row_number}: pair_id {pair_id} does not match "
            f"{project_a_id}__{project_b_id}"
        )
    project_a = _project(projects, project_a_id, "project_a_id", pair_id, row_number, filename)
    project_b = _project(projects, project_b_id, "project_b_id", pair_id, row_number, filename)
    _utility_agrees(row, "project_a_utility", project_a, pair_id, row_number, filename)
    _utility_agrees(row, "project_b_utility", project_b, pair_id, row_number, filename)
    if project_a.utility == project_b.utility:
        raise LoaderError(
            f"{filename} row {row_number}: pair {pair_id} references two "
            f"{project_a.utility} projects"
        )

    precision = _precision(row, row_number, filename)
    schedule_overlap = _flag(row.get("schedule_overlap"), filename, row_number, "schedule_overlap")
    schedule_overlap_months = _number(
        row.get("schedule_overlap_months"), filename, row_number, "schedule_overlap_months"
    )
    if precision != "month" and (
        schedule_overlap is not None or schedule_overlap_months is not None
    ):
        raise LoaderError(
            f"{filename} row {row_number}: temporal_precision {precision or 'blank'} "
            "cannot include schedule overlap months"
        )
    geography_available = _flag(
        row.get("geography_available"), filename, row_number, "geography_available"
    )
    distance = _number(
        row.get("minimum_endpoint_distance_miles"),
        filename,
        row_number,
        "minimum_endpoint_distance_miles",
    )
    geographic_score = _number(
        row.get("geographic_score"), filename, row_number, "geographic_score"
    )
    if geography_available is False and (distance is not None or geographic_score is not None):
        raise LoaderError(
            f"{filename} row {row_number}: unmeasured geography must keep "
            "minimum_endpoint_distance_miles and geographic_score null"
        )
    temporal_data_available = _flag(
        row.get("temporal_data_available"), filename, row_number, "temporal_data_available"
    )
    temporal_score = _number(row.get("temporal_score"), filename, row_number, "temporal_score")
    if temporal_data_available is False and temporal_score is not None:
        raise LoaderError(
            f"{filename} row {row_number}: unavailable timing must keep temporal_score null"
        )
    text_available = _flag(
        row.get("text_similarity_available"), filename, row_number, "text_similarity_available"
    )
    text_raw = _number(row.get("text_similarity_raw"), filename, row_number, "text_similarity_raw")
    text_score = _number(
        row.get("text_similarity_score"), filename, row_number, "text_similarity_score"
    )
    if text_available is False and (text_raw is not None or text_score is not None):
        raise LoaderError(
            f"{filename} row {row_number}: unavailable text similarity must keep "
            "text_similarity_raw and text_similarity_score null"
        )
    infrastructure_available = _flag(
        row.get("infrastructure_similarity_available"),
        filename,
        row_number,
        "infrastructure_similarity_available",
    )
    infrastructure_score = _number(
        row.get("infrastructure_similarity"), filename, row_number, "infrastructure_similarity"
    )
    if infrastructure_available is False and infrastructure_score is not None:
        raise LoaderError(
            f"{filename} row {row_number}: unavailable infrastructure similarity must stay null"
        )
    shared_terms_raw, shared_terms = _shared_terms(row.get("shared_text_terms"))
    try:
        return PairComparison.model_validate(
            {
                "pair_id": pair_id,
                "project_a": project_a,
                "project_b": project_b,
                "geography": {
                    "geography_available": geography_available,
                    "geography_available_both": _flag(
                        row.get("geography_available_both"),
                        filename,
                        row_number,
                        "geography_available_both",
                    ),
                    "geography_point_count_a": _whole_number(
                        row.get("geography_point_count_a"),
                        filename,
                        row_number,
                        "geography_point_count_a",
                    ),
                    "geography_point_count_b": _whole_number(
                        row.get("geography_point_count_b"),
                        filename,
                        row_number,
                        "geography_point_count_b",
                    ),
                    "minimum_endpoint_distance_miles": distance,
                    "project_a_nearest_endpoint": _text(row.get("project_a_nearest_endpoint")),
                    "project_b_nearest_endpoint": _text(row.get("project_b_nearest_endpoint")),
                    "project_a_location_confidence": _text(
                        row.get("project_a_location_confidence")
                    ),
                    "project_b_location_confidence": _text(
                        row.get("project_b_location_confidence")
                    ),
                    "pair_geography_confidence": _text(row.get("pair_geography_confidence")),
                    "geographic_score": geographic_score,
                    "geographic_reason": _text(row.get("geographic_reason")),
                },
                "temporal": {
                    "temporal_data_available": temporal_data_available,
                    "temporal_precision": precision,
                    "schedule_overlap": schedule_overlap,
                    "schedule_overlap_months": schedule_overlap_months,
                    "schedule_overlap_months_are_exact": precision == "month",
                    "same_active_year": _flag(
                        row.get("same_active_year"), filename, row_number, "same_active_year"
                    ),
                    "year_difference": _whole_number(
                        row.get("year_difference"), filename, row_number, "year_difference"
                    ),
                    "temporal_score": temporal_score,
                    "temporal_reason": _text(row.get("temporal_reason")),
                },
                "similarity": {
                    "text_similarity_available": text_available,
                    "text_similarity_raw": text_raw,
                    "text_similarity_score": text_score,
                    "shared_text_terms_raw": shared_terms_raw,
                    "shared_text_terms": shared_terms,
                    "project_type_similarity": _number(
                        row.get("project_type_similarity"),
                        filename,
                        row_number,
                        "project_type_similarity",
                    ),
                    "voltage_similarity": _number(
                        row.get("voltage_similarity"), filename, row_number, "voltage_similarity"
                    ),
                    "infrastructure_similarity_available": infrastructure_available,
                    "infrastructure_similarity": infrastructure_score,
                    "similarity_confidence": _text(row.get("similarity_confidence")),
                },
            }
        )
    except ValidationError as exc:
        raise LoaderError(f"{filename} row {row_number}: {exc}") from exc


def _project(
    projects: dict[str, Project],
    project_id: str,
    field: str,
    pair_id: str,
    row_number: int,
    filename: str,
) -> Project:
    project = projects.get(project_id)
    if project is None:
        raise LoaderError(
            f"{filename} row {row_number}: pair {pair_id} references unknown {field} {project_id}"
        )
    return project


def _utility_agrees(
    row: dict[str, str],
    field: str,
    project: Project,
    pair_id: str,
    row_number: int,
    filename: str,
) -> None:
    utility = _text(row.get(field))
    if utility is not None and utility != project.utility:
        raise LoaderError(
            f"{filename} row {row_number}: pair {pair_id} {field} {utility} "
            f"does not match catalog utility {project.utility}"
        )


def _required_text(row: dict[str, str], field: str, row_number: int, filename: str) -> str:
    value = _text(row.get(field))
    if value is None:
        raise LoaderError(f"{filename} row {row_number}: {field} is required")
    return value


def _precision(
    row: dict[str, str], row_number: int, filename: str
) -> Literal["month", "year", "mixed", "unknown"] | None:
    value = _text(row.get("temporal_precision"))
    if value is None:
        return None
    if value == "month":
        return "month"
    if value == "year":
        return "year"
    if value == "mixed":
        return "mixed"
    if value == "unknown":
        return "unknown"
    raise LoaderError(
        f"{filename} row {row_number}: temporal_precision must be "
        "month, year, mixed, unknown, or blank"
    )


def _shared_terms(value: object) -> tuple[str | None, list[str]]:
    text = _text(value)
    if text is None:
        return None, []
    terms = [part.strip() for part in text.split(";") if part.strip()]
    return text, terms


def _flag(value: object, filename: str, row_number: int, field: str) -> bool | None:
    text = _text(value)
    if text is None:
        return None
    token = text.casefold()
    if token == "true":
        return True
    if token == "false":
        return False
    raise LoaderError(f"{filename} row {row_number}: {field} must be true, false, or blank")


def _whole_number(value: object, filename: str, row_number: int, field: str) -> int | None:
    number = _number(value, filename, row_number, field)
    if number is None:
        return None
    if not number.is_integer():
        raise LoaderError(f"{filename} row {row_number}: {field} must be a whole number or blank")
    return int(number)

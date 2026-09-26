"""Canonical project schema and API response models.

Optional project fields stay null when a source does not provide them.
Null is never a substitute for zero.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DATA_TYPES = ("demo", "public")
_YEAR = re.compile(r"^\d{4}$")
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _is_schedule_value(value: str) -> bool:
    if _YEAR.fullmatch(value):
        return True
    if not _DAY.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


class Project(BaseModel):
    """One normalized utility project."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: str
    utility: str
    project_name: str
    project_type: str | None = None
    description: str | None = None
    voltage_kv: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    geometry: dict[str, Any] | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    capital_cost: float | None = None
    customers_impacted: int | None = None
    source_name: str
    source_url: str | None = None
    source_url_note: str | None = None
    source_document: str | None = None
    source_page: str | None = None
    retrieved_date: str | None = None
    data_type: Literal["demo", "public"]
    provenance_gaps: list[str] = Field(default_factory=list)
    geography_source: str | None = None
    circuit_endpoint_source: str | None = None
    form1_schedule: str | None = None
    date_precision: str | None = None
    estimated_in_service_year: int | None = None
    construction_start: str | None = None
    location_confidence: str | None = None
    location_method: str | None = None
    geometry_type: str | None = None
    unresolved_reason: str | None = None
    from_substation: str | None = None
    to_substation: str | None = None
    from_latitude: float | None = None
    from_longitude: float | None = None
    to_latitude: float | None = None
    to_longitude: float | None = None
    voltage_min_kv: float | None = None
    voltage_label: str | None = None
    ownership_confidence: str | None = None
    ownership_note: str | None = None

    @field_validator("id")
    @classmethod
    def _id_token(cls, value: str) -> str:
        if not _PROJECT_ID.fullmatch(value):
            raise ValueError(
                "id must contain only letters, numbers, dots, underscores, and hyphens"
            )
        return value

    @field_validator(
        "utility",
        "project_name",
        "source_name",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("required text fields cannot be blank")
        return value

    @field_validator("source_url", "source_url_note", mode="before")
    @classmethod
    def _blank_source_url(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("provenance_gaps", mode="before")
    @classmethod
    def _gaps(cls, value: object) -> object:
        if value is None:
            return []
        return value

    @field_validator(
        "project_type",
        "description",
        "status",
        "source_document",
        "source_page",
        "geography_source",
        "circuit_endpoint_source",
        "form1_schedule",
        "date_precision",
        "location_confidence",
        "location_method",
        "geometry_type",
        "unresolved_reason",
        "from_substation",
        "to_substation",
        "voltage_label",
        "ownership_confidence",
        "ownership_note",
        mode="before",
    )
    @classmethod
    def _blank_text_is_null(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("start_date", "end_date", "construction_start")
    @classmethod
    def _schedule_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _is_schedule_value(value):
            raise ValueError("dates must be YYYY or YYYY-MM-DD")
        return value

    @field_validator("retrieved_date")
    @classmethod
    def _retrieved_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _DAY.fullmatch(value):
            raise ValueError("retrieved_date must be YYYY-MM-DD or null")
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("voltage_kv", "voltage_min_kv")
    @classmethod
    def _voltage(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError(
                "voltage must be positive or null; do not use 0 for missing voltage"
            )
        return value

    @field_validator("capital_cost")
    @classmethod
    def _cost(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("capital_cost cannot be negative")
        return value

    @field_validator("customers_impacted")
    @classmethod
    def _customers(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("customers_impacted cannot be negative")
        return value

    @field_validator("geometry")
    @classmethod
    def _geometry(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        if "type" not in value or "coordinates" not in value:
            raise ValueError("geometry must be a GeoJSON object with type and coordinates")
        return value

    @model_validator(mode="after")
    def _coordinates_and_schedule(self) -> Project:
        has_lat = self.latitude is not None
        has_lon = self.longitude is not None
        if has_lat != has_lon:
            raise ValueError("latitude and longitude must both be present or both be null")
        if has_lat and self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if has_lon and self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        if self.start_date and self.end_date:
            if int(self.end_date[:4]) < int(self.start_date[:4]):
                raise ValueError("end_date is before start_date")
            if len(self.start_date) == 10 and len(self.end_date) == 10:
                if self.end_date < self.start_date:
                    raise ValueError("end_date is before start_date")
        self._check_coordinate_pair(self.from_latitude, self.from_longitude, "from")
        self._check_coordinate_pair(self.to_latitude, self.to_longitude, "to")
        if self.data_type == "demo" and not self.source_url:
            raise ValueError("demo records must include source_url")
        missing_url = self.data_type == "public" and not self.source_url
        if missing_url and "source_url" not in self.provenance_gaps:
            self.provenance_gaps = [*self.provenance_gaps, "source_url"]
        return self

    @staticmethod
    def _check_coordinate_pair(
        latitude: float | None,
        longitude: float | None,
        label: str,
    ) -> None:
        if (latitude is None) != (longitude is None):
            raise ValueError(f"{label} latitude and longitude must both be present or both be null")
        if latitude is not None and not -90 <= latitude <= 90:
            raise ValueError(f"{label} latitude must be between -90 and 90")
        if longitude is not None and not -180 <= longitude <= 180:
            raise ValueError(f"{label} longitude must be between -180 and 180")


class DataEnvelope(BaseModel):
    dataset_status: Literal["demo", "verified_public", "mixed", "empty"]
    data_notice: str
    contains_demo_data: bool
    contains_verified_public_data: bool


class HealthResponse(DataEnvelope):
    status: Literal["ok"] = "ok"
    service: str = "gridsync"
    analysis_dataset_status: Literal["demo", "verified_public", "mixed", "empty"] | None = None
    analysis_data_notice: str | None = None


class UtilitySummary(BaseModel):
    name: str
    project_count: int
    data_types: list[Literal["demo", "public"]]


class UtilityListResponse(DataEnvelope):
    utilities: list[UtilitySummary]


class ProjectListResponse(DataEnvelope):
    count: int
    projects: list[Project]


class ProjectResponse(DataEnvelope):
    project: Project


class FeatureVector(BaseModel):
    """Measured pair features. Unavailable measurements are null, not zero."""

    distance_miles: float | None
    distance_km: float | None
    distance_method: Literal["point_haversine", "linestring_vertices"] | None
    distance_label: str | None = None
    proximity_band: Literal["very_strong", "strong", "moderate", "weak"] | None
    distance_similarity: float | None
    temporal_precision: Literal["day", "month", "year", "mixed", "unknown", "unavailable"] | None
    start_date_difference: int | None
    end_date_difference: int | None
    start_year_difference: int | None
    end_year_difference: int | None
    overlap_days: int | None
    schedule_overlap_months: float | None
    overlap_years: int | None
    overlapping_years: list[int] | None
    schedule_overlap_ratio: float | None
    schedule_similarity: float | None
    overlap_kind: Literal["identical", "full", "partial", "none"] | None
    year_difference: float | None = None
    same_active_year: bool | None = None
    project_type_similarity: float | None
    voltage_similarity: float | None
    status_similarity: float | None
    text_similarity: float | None
    cost_similarity: float | None
    project_similarity: float | None
    infrastructure_similarity: float | None


class ScoreComponent(BaseModel):
    name: Literal[
        "geographic_proximity",
        "schedule_overlap",
        "project_similarity",
        "infrastructure_similarity",
    ]
    value: float | None
    base_weight: float
    effective_weight: float
    available: bool


class SharedResource(BaseModel):
    resource: str
    label: str
    strength: Literal["HIGH", "MEDIUM", "LOW"]
    reason: str


class CoordinationResource(BaseModel):
    """Resource row Rob's frontend reads from coordination_package.resources."""

    name: str
    resource: str
    label: str
    strength: Literal["HIGH", "MEDIUM", "LOW"]
    potential: Literal["HIGH", "MEDIUM", "LOW"]
    reason: str
    evidence: list[str] = Field(default_factory=list)


class CoordinationPackage(BaseModel):
    shared_resources: list[SharedResource]
    resources: list[CoordinationResource] = Field(default_factory=list)
    evidence_note: str


class PublishedComponents(BaseModel):
    """Aaron's 0–100 component scores, copied beside the 0–1 API feature fields."""

    geographic_score: float | None = None
    temporal_score: float | None = None
    text_similarity_score: float | None = None
    infrastructure_similarity: float | None = None
    scale: Literal["0_to_100"] = "0_to_100"
    score_confidence: str | None = None
    opportunity_rank: int | None = None
    geography_available: bool | None = None


class DataConfidence(BaseModel):
    geography: str | None = None
    temporal: str | None = None
    similarity: str | None = None
    overall_score: str | None = None


class Opportunity(BaseModel):
    id: str
    project_a: Project
    project_b: Project
    features: FeatureVector
    features_used: list[str]
    coordination_score: float | None
    score_interpretation: str
    base_weights: dict[str, float]
    effective_weights: dict[str, float]
    components: list[ScoreComponent]
    reasons: list[str]
    evidence_gaps: list[str]
    coordination_package: CoordinationPackage
    data_type: Literal["demo", "public", "mixed"]
    coarse_filter_excluded: bool
    published_components: PublishedComponents | None = None
    data_confidence: DataConfidence | None = None


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utility_a: str = Field(min_length=1)
    utility_b: str = Field(min_length=1)
    year: int | None = Field(default=None, ge=1900, le=2200)
    project_type: str | None = None
    max_distance_miles: float | None = Field(default=None, ge=0)
    min_coordination_score: float | None = Field(default=None, ge=0, le=100)


class AnalyzeResponse(DataEnvelope):
    score_interpretation: str
    utility_a: str
    utility_b: str
    projects_analyzed: int
    pairs_evaluated: int
    pairs_discarded: int
    discard_reasons: dict[str, int]
    opportunity_count: int
    high_opportunity_count: int
    high_opportunity_minimum: float
    high_opportunity_note: str
    weights: dict[str, float]
    thresholds: dict[str, float]
    opportunities: list[Opportunity]


class OpportunityResponse(DataEnvelope):
    score_interpretation: str
    opportunity: Opportunity


class AssistantQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=1000)
    utility_a: str | None = None
    utility_b: str | None = None


class AssistantResponse(DataEnvelope):
    assistant_mode: Literal["structured_retrieval"]
    llm_used: bool
    llm_configured: bool
    answer: str
    note: str
    filters_applied: dict[str, Any]
    opportunities: list[Opportunity]

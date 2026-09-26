"""Configurable thresholds and scoring weights.

Initial prototype weights are geographic 40%, schedule 30%, project 20%,
and infrastructure 10%. Proximity bands are GridSync heuristics, not
official utility-industry thresholds.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCORE_INTERPRETATION = (
    "The coordination score measures the strength of a potential coordination "
    "opportunity from available evidence. It is not a probability of coordination, "
    "a probability of success, expected savings, financial ROI, or a recommendation "
    "to coordinate."
)


class Settings(BaseModel):
    """Analysis configuration. Missing measurements are never filled with zero."""

    model_config = ConfigDict(frozen=True)

    data_file: str | None = None
    project_catalog: Literal["demo", "processed"] = "demo"

    weight_geographic: Decimal = Decimal("0.40")
    weight_schedule: Decimal = Decimal("0.30")
    weight_project: Decimal = Decimal("0.20")
    weight_infrastructure: Decimal = Decimal("0.10")

    project_type_share: Decimal = Decimal("0.50")
    project_text_share: Decimal = Decimal("0.50")
    infrastructure_voltage_share: Decimal = Decimal("0.70")
    infrastructure_status_share: Decimal = Decimal("0.30")

    proximity_very_strong_miles: float = 10.0
    proximity_strong_miles: float = 25.0
    proximity_moderate_miles: float = 50.0
    distance_similarity_zero_miles: float = 100.0
    max_pair_distance_miles: float = 100.0

    min_text_tokens: int = Field(default=3, ge=1)
    resource_high_distance_miles: float = 25.0
    resource_meaningful_overlap_ratio: float = 0.25
    resource_type_similarity_min: float = 1.0
    high_opportunity_minimum: float = 75.0

    @classmethod
    def from_env(cls) -> Settings:
        raw_path = os.environ.get("GRIDSYNC_DATA_FILE", "").strip()
        requested = os.environ.get("GRIDSYNC_PROJECT_CATALOG", "").strip().lower()
        catalog: Literal["demo", "processed"]
        if requested in {"", "auto"}:
            from app.processed_loader import processed_files_available

            catalog = "processed" if processed_files_available() else "demo"
        elif requested == "demo":
            catalog = "demo"
        elif requested == "processed":
            catalog = "processed"
        else:
            raise ValueError("GRIDSYNC_PROJECT_CATALOG must be demo, processed, or auto")
        return cls(data_file=raw_path or None, project_catalog=catalog)

    @model_validator(mode="after")
    def _check_bounds(self) -> Settings:
        weights = (
            self.weight_geographic
            + self.weight_schedule
            + self.weight_project
            + self.weight_infrastructure
        )
        if weights != Decimal("1.00"):
            raise ValueError("Scoring weights must sum to 1.00")
        anchors = (
            self.proximity_very_strong_miles,
            self.proximity_strong_miles,
            self.proximity_moderate_miles,
            self.distance_similarity_zero_miles,
        )
        if anchors != tuple(sorted(anchors)) or len(set(anchors)) != len(anchors):
            raise ValueError("Proximity mile thresholds must be strictly increasing")
        if min(anchors) <= 0:
            raise ValueError("Proximity mile thresholds must be positive")
        if self.max_pair_distance_miles <= 0:
            raise ValueError("max_pair_distance_miles must be positive")
        if not 0 <= self.resource_meaningful_overlap_ratio <= 1:
            raise ValueError("resource_meaningful_overlap_ratio must be between 0 and 1")
        if not 0 <= self.resource_type_similarity_min <= 1:
            raise ValueError("resource_type_similarity_min must be between 0 and 1")
        if not 0 <= self.high_opportunity_minimum <= 100:
            raise ValueError("high_opportunity_minimum must be between 0 and 100")
        return self

    def base_weights(self) -> dict[str, Decimal]:
        return {
            "geographic_proximity": self.weight_geographic,
            "schedule_overlap": self.weight_schedule,
            "project_similarity": self.weight_project,
            "infrastructure_similarity": self.weight_infrastructure,
        }

    def public_weights(self) -> dict[str, float]:
        return {name: float(value) for name, value in self.base_weights().items()}

    def public_thresholds(self) -> dict[str, float]:
        return {
            "max_pair_distance_miles": self.max_pair_distance_miles,
            "very_strong_proximity_miles": self.proximity_very_strong_miles,
            "strong_proximity_miles": self.proximity_strong_miles,
            "moderate_proximity_miles": self.proximity_moderate_miles,
            "distance_similarity_zero_miles": self.distance_similarity_zero_miles,
            "resource_high_distance_miles": self.resource_high_distance_miles,
            "resource_meaningful_overlap_ratio": self.resource_meaningful_overlap_ratio,
            "resource_type_similarity_min": self.resource_type_similarity_min,
            "high_opportunity_minimum": self.high_opportunity_minimum,
        }

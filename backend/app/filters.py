"""Request filters shared by the demo engine and the public analysis adapter."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OpportunityFilters:
    year: int | None = None
    project_type: str | None = None
    max_distance_miles: float | None = None
    min_coordination_score: float | None = None

"""Deterministic geographic distance.

Point projects use haversine distance. LineString geometry uses the minimum
haversine between vertices. That vertex distance is not a full geodesic route
buffer. Missing coordinates stay null and are never treated as zero miles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from app.config import Settings
from app.models import Project

EARTH_RADIUS_MILES = 3958.7613
EARTH_RADIUS_KM = 6371.0088

ProximityBand = Literal["very_strong", "strong", "moderate", "weak"]
DistanceMethod = Literal["point_haversine", "linestring_vertices"]

_BAND_LABELS = {
    "very_strong": "very strong",
    "strong": "strong",
    "moderate": "moderate",
    "weak": "weak",
}


@dataclass(frozen=True)
class GeographicComparison:
    distance_miles: float | None
    distance_km: float | None
    distance_method: DistanceMethod | None
    proximity_band: ProximityBand | None
    distance_similarity: float | None
    reasons: tuple[str, ...]
    evidence_gaps: tuple[str, ...]


def haversine(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> tuple[float, float]:
    """Return distance in miles and kilometers."""
    phi_a = math.radians(latitude_a)
    phi_b = math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    haversine_component = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    central_angle = 2 * math.atan2(
        math.sqrt(haversine_component),
        math.sqrt(max(0.0, 1 - haversine_component)),
    )
    return EARTH_RADIUS_MILES * central_angle, EARTH_RADIUS_KM * central_angle


def proximity_band(distance_miles: float, settings: Settings) -> ProximityBand:
    if distance_miles <= settings.proximity_very_strong_miles:
        return "very_strong"
    if distance_miles <= settings.proximity_strong_miles:
        return "strong"
    if distance_miles <= settings.proximity_moderate_miles:
        return "moderate"
    return "weak"


def distance_similarity(distance_miles: float, settings: Settings) -> float:
    """Map miles to 0–1 with linear segments at the prototype band edges."""
    miles = max(0.0, distance_miles)
    anchors = (
        (0.0, 1.0),
        (settings.proximity_very_strong_miles, 0.75),
        (settings.proximity_strong_miles, 0.50),
        (settings.proximity_moderate_miles, 0.25),
        (settings.distance_similarity_zero_miles, 0.0),
    )
    if miles >= anchors[-1][0]:
        return 0.0
    segments = zip(anchors, anchors[1:], strict=False)
    for (start_miles, start_score), (end_miles, end_score) in segments:
        if miles <= end_miles:
            span = end_miles - start_miles
            fraction = (miles - start_miles) / span
            return start_score + (end_score - start_score) * fraction
    return 0.0


def compare_projects(
    project_a: Project,
    project_b: Project,
    settings: Settings,
) -> GeographicComparison:
    measured = _pair_distance(project_a, project_b)
    if measured is None:
        missing: list[str] = []
        for project in (project_a, project_b):
            if _line_vertices(project.geometry):
                continue
            if project.latitude is None or project.longitude is None:
                missing.append(project.id)
        if not missing:
            missing = [project_a.id, project_b.id]
        joined = ", ".join(missing)
        return GeographicComparison(
            distance_miles=None,
            distance_km=None,
            distance_method=None,
            proximity_band=None,
            distance_similarity=None,
            reasons=(),
            evidence_gaps=(
                f"Coordinates are missing for {joined}; distance was not calculated "
                "and was not treated as zero.",
            ),
        )
    miles, kilometers, method = measured
    band = proximity_band(miles, settings)
    similarity = distance_similarity(miles, settings)
    method_note = ""
    if method == "linestring_vertices":
        method_note = (
            " Distance uses the minimum haversine between LineString vertices, "
            "not a geodesic buffer around the route."
        )
    reason = (
        f"Projects are {_format_miles(miles)} miles apart "
        f"({_BAND_LABELS[band]} geographic proximity). "
        "This proximity band is a GridSync prototype heuristic, not an official "
        f"utility threshold.{method_note}"
    )
    return GeographicComparison(
        distance_miles=miles,
        distance_km=kilometers,
        distance_method=method,
        proximity_band=band,
        distance_similarity=similarity,
        reasons=(reason,),
        evidence_gaps=(),
    )


def _pair_distance(
    project_a: Project,
    project_b: Project,
) -> tuple[float, float, DistanceMethod] | None:
    vertices_a = _line_vertices(project_a.geometry)
    vertices_b = _line_vertices(project_b.geometry)
    if vertices_a and vertices_b:
        return (*_minimum_distance(vertices_a, vertices_b), "linestring_vertices")
    point_b = _point(project_b)
    if vertices_a and point_b is not None:
        return (*_minimum_distance(vertices_a, [point_b]), "linestring_vertices")
    point_a = _point(project_a)
    if vertices_b and point_a is not None:
        return (*_minimum_distance([point_a], vertices_b), "linestring_vertices")
    if point_a is not None and point_b is not None:
        miles, kilometers = haversine(point_a[0], point_a[1], point_b[0], point_b[1])
        return miles, kilometers, "point_haversine"
    return None


def _point(project: Project) -> tuple[float, float] | None:
    if project.latitude is None or project.longitude is None:
        return None
    return project.latitude, project.longitude


def _line_vertices(geometry: object) -> list[tuple[float, float]]:
    if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
        return []
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list):
        return []
    vertices: list[tuple[float, float]] = []
    for coordinate in coordinates:
        if not isinstance(coordinate, list | tuple) or len(coordinate) < 2:
            continue
        longitude, latitude = coordinate[0], coordinate[1]
        if isinstance(longitude, int | float) and isinstance(latitude, int | float):
            vertices.append((float(latitude), float(longitude)))
    if len(vertices) < 2:
        return []
    return vertices


def _minimum_distance(
    left: list[tuple[float, float]],
    right: list[tuple[float, float]],
) -> tuple[float, float]:
    best_miles: float | None = None
    best_km: float | None = None
    for lat_a, lon_a in left:
        for lat_b, lon_b in right:
            miles, kilometers = haversine(lat_a, lon_a, lat_b, lon_b)
            if best_miles is None or miles < best_miles:
                best_miles = miles
                best_km = kilometers
    if best_miles is None or best_km is None:
        raise ValueError("vertex distance requires at least one pair of coordinates")
    return best_miles, best_km


def _format_miles(distance_miles: float) -> str:
    return f"{distance_miles:.1f}"

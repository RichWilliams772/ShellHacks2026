"""Known haversine distances, bands, and missing coordinates."""

from __future__ import annotations

import math

from app.config import Settings
from app.geographic import (
    EARTH_RADIUS_KM,
    EARTH_RADIUS_MILES,
    compare_projects,
    distance_similarity,
    haversine,
    proximity_band,
)
from tests.helpers import make_project

SETTINGS = Settings()


def test_equator_one_degree_matches_arc_length() -> None:
    miles, kilometers = haversine(0, 0, 0, 1)
    assert math.isclose(miles, EARTH_RADIUS_MILES * math.pi / 180, rel_tol=1e-9)
    assert math.isclose(kilometers, EARTH_RADIUS_KM * math.pi / 180, rel_tol=1e-9)


def test_quarter_circumference_along_equator() -> None:
    miles, kilometers = haversine(0, 0, 0, 90)
    assert math.isclose(miles, EARTH_RADIUS_MILES * math.pi / 2, rel_tol=1e-9)
    assert math.isclose(kilometers, EARTH_RADIUS_KM * math.pi / 2, rel_tol=1e-9)


def test_identical_point_is_zero() -> None:
    assert haversine(28.5, -81.3, 28.5, -81.3) == (0.0, 0.0)


def test_proximity_bands_follow_configured_edges() -> None:
    assert proximity_band(0, SETTINGS) == "very_strong"
    assert proximity_band(10, SETTINGS) == "very_strong"
    assert proximity_band(10.01, SETTINGS) == "strong"
    assert proximity_band(25, SETTINGS) == "strong"
    assert proximity_band(25.01, SETTINGS) == "moderate"
    assert proximity_band(50, SETTINGS) == "moderate"
    assert proximity_band(50.01, SETTINGS) == "weak"


def test_distance_similarity_anchors() -> None:
    assert distance_similarity(0, SETTINGS) == 1.0
    assert distance_similarity(10, SETTINGS) == 0.75
    assert distance_similarity(25, SETTINGS) == 0.5
    assert distance_similarity(50, SETTINGS) == 0.25
    assert distance_similarity(100, SETTINGS) == 0.0
    assert distance_similarity(150, SETTINGS) == 0.0


def test_missing_coordinates_are_null_not_zero() -> None:
    left = make_project(id="DUKE-DEMO-A", latitude=None, longitude=None)
    right = make_project(
        id="TECO-DEMO-B",
        utility="Tampa Electric",
        latitude=28.1,
        longitude=-82.1,
    )
    result = compare_projects(left, right, SETTINGS)
    assert result.distance_miles is None
    assert result.distance_km is None
    assert result.distance_similarity is None
    assert result.proximity_band is None
    assert "not treated as zero" in result.evidence_gaps[0]
    assert "DUKE-DEMO-A" in result.evidence_gaps[0]


def test_linestring_vertex_distance_uses_closest_vertex() -> None:
    line = make_project(
        id="DUKE-DEMO-LINE",
        latitude=None,
        longitude=None,
        geometry={"type": "LineString", "coordinates": [[0, 0], [1, 0]]},
    )
    point = make_project(
        id="TECO-DEMO-POINT",
        utility="Tampa Electric",
        latitude=0,
        longitude=0,
    )
    result = compare_projects(line, point, SETTINGS)
    assert result.distance_miles == 0
    assert result.distance_method == "linestring_vertices"

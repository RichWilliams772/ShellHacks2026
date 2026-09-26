# Aaron Green
# Checks the distance math and geographic scoring in analysis/geographic.py.

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.geographic import (  # noqa: E402
    calculate_endpoint_proximity, extract_endpoints, geographic_score,
    haversine_miles, is_valid_coordinate, minimum_endpoint_distance,
    pair_geography_confidence,
)

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f" -- {detail}" if detail else ""))
        failures.append(name)


def test_haversine_identity():
    check("identical coordinates give ~0 distance",
          math.isclose(haversine_miles(28.0, -82.0, 28.0, -82.0), 0.0, abs_tol=1e-9))


def test_haversine_symmetry():
    a = haversine_miles(27.938069, -82.440138, 28.022843, -82.481015)
    b = haversine_miles(28.022843, -82.481015, 27.938069, -82.440138)
    check("haversine is symmetric", math.isclose(a, b, rel_tol=1e-12), f"{a} vs {b}")


def test_haversine_known_distance():
    # Gannon <-> Juneau, TECO circuit 230037's own endpoints from Task 1.
    miles = haversine_miles(27.938069, -82.440138, 28.022843, -82.481015)
    check("known Gannon-Juneau distance is plausible", 6.0 < miles < 6.8, f"got {miles:.3f}")


def test_four_endpoint_minimum():
    # A has two points 100 miles apart; B sits close to A's second point only.
    points_a = {"origin": (25.0, -80.0), "destination": (27.0, -80.0)}
    points_b = {"origin": (27.01, -80.0)}
    distance, nearest_a, nearest_b = minimum_endpoint_distance(points_a, points_b)
    check("four-endpoint search finds the true minimum",
          distance is not None and distance < 1, f"got {distance}")
    check("nearest endpoint on A is the close one", nearest_a == "destination", nearest_a)
    check("nearest endpoint on B is correct", nearest_b == "origin", nearest_b)

    # Cross-check against a brute-force computation of all four combinations.
    brute = min(
        haversine_miles(25.0, -80.0, 27.01, -80.0),
        haversine_miles(27.0, -80.0, 27.01, -80.0),
    )
    check("minimum matches brute-force of all combinations",
          math.isclose(distance, brute, rel_tol=1e-9))


def test_partial_endpoints():
    # Project A is a corridor (two points), project B is a single point (CASE B).
    points_a = extract_endpoints(25.0, -80.0, 25.5, -80.5)
    points_b = extract_endpoints(25.6, -80.6, None, None)
    check("corridor project yields two points", len(points_a) == 2)
    check("point project yields one point", len(points_b) == 1)
    distance, nearest_a, nearest_b = minimum_endpoint_distance(points_a, points_b)
    check("partial-endpoint distance is computed", distance is not None)
    check("nearest endpoint on the corridor side is its destination",
          nearest_a == "destination", nearest_a)


def test_missing_coordinates_return_null():
    points_a = extract_endpoints(None, None, None, None)
    points_b = extract_endpoints(25.0, -80.0, None, None)
    check("project with no coordinates yields zero points", len(points_a) == 0)
    distance, nearest_a, nearest_b = minimum_endpoint_distance(points_a, points_b)
    check("missing coordinates on one side give null distance", distance is None)
    check("null distance gives null nearest labels", nearest_a is None and nearest_b is None)
    check("null distance gives null geographic_score", geographic_score(distance) is None)


def test_invalid_coordinates_are_rejected():
    check("latitude 91 is invalid", not is_valid_coordinate(91, 0))
    check("longitude 181 is invalid", not is_valid_coordinate(0, 181))
    check("latitude -91 is invalid", not is_valid_coordinate(-91, 0))
    check("NaN is invalid", not is_valid_coordinate(float("nan"), 0))
    check("valid coordinate passes", is_valid_coordinate(27.9, -82.4))

    # An out-of-range coordinate must be dropped, not silently used or zeroed.
    points = extract_endpoints(91.0, -82.0, 27.9, -82.4)
    check("an invalid endpoint is dropped, not corrected",
          "origin" not in points and "destination" in points, points)


def test_geographic_score_boundaries():
    cases = [
        (0, 100), (10, 100), (10.01, 80),
        (25, 80), (25.01, 50),
        (50, 50), (50.01, 20),
        (100, 20), (100.01, 0),
        (500, 0),
    ]
    for distance, expected in cases:
        got = geographic_score(distance)
        check(f"geographic_score({distance}) == {expected}", got == expected, f"got {got}")
    check("geographic_score(None) is None", geographic_score(None) is None)


def test_pair_geography_confidence():
    check("HIGH+HIGH -> HIGH", pair_geography_confidence("HIGH", "HIGH") == "HIGH")
    check("HIGH+MEDIUM -> MEDIUM", pair_geography_confidence("HIGH", "MEDIUM") == "MEDIUM")
    check("MEDIUM+MEDIUM -> MEDIUM", pair_geography_confidence("MEDIUM", "MEDIUM") == "MEDIUM")
    check("HIGH+UNKNOWN -> UNKNOWN", pair_geography_confidence("HIGH", "UNKNOWN") == "UNKNOWN")
    check("HIGH+LOW -> UNKNOWN", pair_geography_confidence("HIGH", "LOW") == "UNKNOWN")
    check("confidence is a string, not a probability",
          isinstance(pair_geography_confidence("HIGH", "HIGH"), str))


def test_full_feature_missing_geography_gives_null_not_zero():
    project_a = {"from_lat": 28.0, "from_lon": -82.0, "to_lat": 28.1, "to_lon": -82.1,
                "location_confidence": "HIGH"}
    project_b = {"from_lat": None, "from_lon": None, "to_lat": None, "to_lon": None,
                "location_confidence": "UNKNOWN"}
    features = calculate_endpoint_proximity(project_a, project_b)
    check("geography_available is False when one side has no coordinates",
          features["geography_available"] is False)
    check("distance is null, not zero", features["minimum_endpoint_distance_miles"] is None)
    check("geographic_score is null, not zero", features["geographic_score"] is None)
    check("pair_geography_confidence is UNKNOWN",
          features["pair_geography_confidence"] == "UNKNOWN")


def main():
    test_haversine_identity()
    test_haversine_symmetry()
    test_haversine_known_distance()
    test_four_endpoint_minimum()
    test_partial_endpoints()
    test_missing_coordinates_return_null()
    test_invalid_coordinates_are_rejected()
    test_geographic_score_boundaries()
    test_pair_geography_confidence()
    test_full_feature_missing_geography_gives_null_not_zero()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

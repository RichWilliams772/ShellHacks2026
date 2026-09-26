# Aaron Green
# Measures how close a Duke project and a TECO project actually are, using only real coordinates.

import math

# Same value used in Task 1's geography build, so a distance computed there and
# a distance computed here never disagree over which Earth radius was used.
EARTH_RADIUS_MILES = 3958.7613

# A straight line between two endpoints is an approximate corridor, not the
# physical route of the transmission line. Every name and reason string below
# says "endpoint distance", never "route" or "line distance".
ENDPOINT_LABELS = ("origin", "destination")

# Mirrors PROJECT_SPEC.md's proximity bands (0-10 / 10-25 / 25-50 / 50+ miles).
# The spec describes those bands qualitatively; the 0-100 numbers are Task 3's
# own prototype heuristic, not an industry standard. Boundaries are inclusive
# on the lower band: distance <= threshold gets that band's score.
GEOGRAPHIC_SCORE_THRESHOLDS = [
    (10, 100),
    (25, 80),
    (50, 50),
    (100, 20),
]
GEOGRAPHIC_SCORE_BEYOND_MAX = 0

# Pair-level confidence from the two project-level confidences already set in
# Tasks 1 and 2. Never overwrites either project's own confidence field.
#   HIGH + HIGH     -> HIGH
#   HIGH/MEDIUM + MEDIUM -> MEDIUM
#   anything with LOW or UNKNOWN -> UNKNOWN
_CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}


def is_valid_coordinate(lat, lon):
    """-90..90 / -180..180. Never mistake an out-of-range value for missing."""
    if lat is None or lon is None:
        return False
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    if math.isnan(lat) or math.isnan(lon):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in miles. Deterministic; no model involved."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def extract_endpoints(from_lat, from_lon, to_lat, to_lon):
    """Named, validated points for one project. 0, 1, or 2 entries.

    A corridor project contributes both "origin" (from) and "destination" (to).
    A point project (only one substation located) contributes just "origin".
    Invalid coordinates are dropped, not corrected.
    """
    points = {}
    if is_valid_coordinate(from_lat, from_lon):
        points["origin"] = (float(from_lat), float(from_lon))
    if is_valid_coordinate(to_lat, to_lon):
        points["destination"] = (float(to_lat), float(to_lon))
    return points


def minimum_endpoint_distance(points_a, points_b):
    """The smallest distance across every combination of A's and B's points.

    Returns (distance_miles, nearest_label_a, nearest_label_b), or
    (None, None, None) if either project has no valid point at all.
    This is CASE D from TASK_3: no coordinates means no distance, not zero.
    """
    if not points_a or not points_b:
        return None, None, None

    best = None
    for label_a, point_a in points_a.items():
        for label_b, point_b in points_b.items():
            distance = haversine_miles(*point_a, *point_b)
            if best is None or distance < best[0]:
                best = (distance, label_a, label_b)
    return best


def geographic_score(distance_miles):
    """0-100 prototype heuristic. Null distance stays null, never zero."""
    if distance_miles is None:
        return None
    for threshold, score in GEOGRAPHIC_SCORE_THRESHOLDS:
        if distance_miles <= threshold:
            return score
    return GEOGRAPHIC_SCORE_BEYOND_MAX


def pair_geography_confidence(confidence_a, confidence_b):
    """Combine two project-level confidences into one pair-level label.

    Categorical only - HIGH/MEDIUM/UNKNOWN, never a number standing in for one.
    A LOW on either side is treated the same as UNKNOWN: approximate geography
    is not solid enough ground to call a pair's location MEDIUM or better.
    """
    rank_a = _CONFIDENCE_RANK.get(confidence_a, 0)
    rank_b = _CONFIDENCE_RANK.get(confidence_b, 0)
    if rank_a <= 1 or rank_b <= 1:
        return "UNKNOWN"
    if rank_a >= 3 and rank_b >= 3:
        return "HIGH"
    return "MEDIUM"


def geographic_reason(distance_miles, nearest_a, nearest_b):
    """A plain sentence a judge can read, generated only from calculated values."""
    if distance_miles is None:
        return "Insufficient location data to estimate distance between these projects."
    return (f"Known project endpoints are approximately {distance_miles:.1f} miles "
            f"apart (Duke's {nearest_a}, TECO's {nearest_b}).")


def calculate_endpoint_proximity(project_a, project_b):
    """Full geographic feature set for one Duke x TECO row.

    project_a / project_b: dicts with from_lat, from_lon, to_lat, to_lon,
    location_confidence.
    """
    points_a = extract_endpoints(project_a.get("from_lat"), project_a.get("from_lon"),
                                 project_a.get("to_lat"), project_a.get("to_lon"))
    points_b = extract_endpoints(project_b.get("from_lat"), project_b.get("from_lon"),
                                 project_b.get("to_lat"), project_b.get("to_lon"))

    distance, nearest_a, nearest_b = minimum_endpoint_distance(points_a, points_b)

    return {
        "geography_available": distance is not None,
        "geography_point_count_a": len(points_a),
        "geography_point_count_b": len(points_b),
        "minimum_endpoint_distance_miles": (round(distance, 2)
                                            if distance is not None else None),
        "project_a_nearest_endpoint": nearest_a,
        "project_b_nearest_endpoint": nearest_b,
        "pair_geography_confidence": pair_geography_confidence(
            project_a.get("location_confidence"), project_b.get("location_confidence")),
        "geographic_score": geographic_score(distance),
        "geographic_reason": geographic_reason(distance, nearest_a, nearest_b),
    }

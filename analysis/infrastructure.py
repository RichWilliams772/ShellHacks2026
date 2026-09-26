# Aaron Green
# Compares the structured infrastructure attributes of a Duke project and a TECO project.

import math

# line_type and AC/DC exist as columns in Our Grid Future's schema, but are
# blank for every one of the 10 Duke projects actually used here (checked
# directly against the raw workbook), and TECO's schema never had them at all.
# Rather than emit an always-null column pretending to compare something that
# was never measured, those components are simply not part of this module.
# If a future data source populates them, add a function here the same way
# project_type/voltage are done below - nothing structural needs to change.

# Same normalized type -> fully compatible, different -> not, per TASK_4
# section 21: "For the MVP, exact normalized type matching may be sufficient."
# A small compatibility ontology (e.g. transmission_upgrade partially matches
# transmission_line) was considered and rejected - it would be an invented
# judgment call with no source backing it, for a hackathon that does not need
# it to tell its story.
UNKNOWN_TYPE_VALUES = {None, "", "unknown"}

# Voltage gap (kV) -> similarity. Ranges that overlap at all score 100 outright
# regardless of gap. Otherwise this maps the distance between the two nearest
# range edges. Thresholds picked from the actual gaps this dataset produces
# (0, 46, 161 kV) with headroom between them, not tuned to a target answer.
VOLTAGE_GAP_THRESHOLDS = [
    (75, 70),
    (150, 40),
]
VOLTAGE_GAP_BEYOND_MAX = 15

# project type = 50%, voltage = 35%. TASK_4's own recommended prototype
# starting point (section 31); PROJECT_SPEC does not define numeric weights
# for this component, so there is nothing to defer to instead.
INFRASTRUCTURE_WEIGHTS = {"project_type": 50, "voltage": 35}


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def calculate_project_type_similarity(type_a, type_b):
    """100 = same normalized type, 0 = different, None = either is missing/unknown.

    Missing does not mean incompatible - it means there is nothing to compare.
    """
    norm_a = str(type_a).strip().lower() if not _is_missing(type_a) else None
    norm_b = str(type_b).strip().lower() if not _is_missing(type_b) else None
    if norm_a in UNKNOWN_TYPE_VALUES or norm_b in UNKNOWN_TYPE_VALUES:
        return None
    if norm_a is None or norm_b is None:
        return None
    return 100 if norm_a == norm_b else 0


def _voltage_range(min_kv, max_kv):
    """A usable (low, high) pair, or None if voltage is not known at all."""
    if _is_missing(min_kv) and _is_missing(max_kv):
        return None
    low = min_kv if not _is_missing(min_kv) else max_kv
    high = max_kv if not _is_missing(max_kv) else min_kv
    return (float(low), float(high))


def _voltage_gap(range_a, range_b):
    """0 if the two ranges overlap at all, else the distance between their nearest edges."""
    low_a, high_a = range_a
    low_b, high_b = range_b
    if low_a <= high_b and low_b <= high_a:
        return 0.0
    return low_b - high_a if low_b > high_a else low_a - high_b


def calculate_voltage_similarity(min_a, max_a, min_b, max_b):
    """100 = overlapping voltage range/class, lower = wider apart, None = voltage unknown on a side."""
    range_a, range_b = _voltage_range(min_a, max_a), _voltage_range(min_b, max_b)
    if range_a is None or range_b is None:
        return None
    gap = _voltage_gap(range_a, range_b)
    if gap <= 0:
        return 100
    for threshold, score in VOLTAGE_GAP_THRESHOLDS:
        if gap <= threshold:
            return score
    return VOLTAGE_GAP_BEYOND_MAX


def weighted_available_average(scores, weights):
    """Average only the components that are actually available, reweighted to sum to 1.

    scores / weights: dicts keyed by the same component names. A component
    missing from `scores` (value None) is left out of both the numerator and
    the denominator - never treated as a 0.
    """
    available = {name: value for name, value in scores.items() if value is not None}
    if not available:
        return None
    total_weight = sum(weights[name] for name in available)
    if total_weight == 0:
        return None
    return sum(available[name] * weights[name] for name in available) / total_weight


def calculate_infrastructure_similarity(project_a, project_b):
    """Full structured-similarity feature set for one Duke x TECO row.

    project_a / project_b: dicts with project_type, voltage_min_kv, voltage_max_kv.
    """
    type_similarity = calculate_project_type_similarity(
        project_a.get("project_type"), project_b.get("project_type"))
    voltage_similarity = calculate_voltage_similarity(
        project_a.get("voltage_min_kv"), project_a.get("voltage_max_kv"),
        project_b.get("voltage_min_kv"), project_b.get("voltage_max_kv"))

    combined = weighted_available_average(
        {"project_type": type_similarity, "voltage": voltage_similarity},
        INFRASTRUCTURE_WEIGHTS)

    return {
        "project_type_similarity": type_similarity,
        "voltage_similarity": voltage_similarity,
        "infrastructure_similarity_available": combined is not None,
        "infrastructure_similarity": round(combined, 2) if combined is not None else None,
    }


def similarity_confidence(text_available, type_similarity, voltage_similarity):
    """HIGH/MEDIUM/LOW/UNKNOWN - describes how much evidence supported the
    comparison, NOT how similar the projects turned out to be. A pair can be
    HIGH confidence and low similarity: that means we are confident they are
    dissimilar.
    """
    available = sum([
        bool(text_available),
        type_similarity is not None,
        voltage_similarity is not None,
    ])
    return {3: "HIGH", 2: "MEDIUM", 1: "LOW"}.get(available, "UNKNOWN")

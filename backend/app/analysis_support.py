"""Map scored feature names to the measurements that produced them."""

from __future__ import annotations

_RAW_FEATURES: dict[str, tuple[str, ...]] = {
    "distance_similarity": ("distance_miles", "distance_km", "distance_similarity"),
    "schedule_similarity": ("schedule_overlap_ratio", "schedule_similarity"),
    "project_type_similarity": ("project_type_similarity",),
    "text_similarity": ("text_similarity",),
    "voltage_similarity": ("voltage_similarity",),
    "status_similarity": ("status_similarity",),
}


def measured_features(score_features: tuple[str, ...], temporal_precision: str) -> list[str]:
    """List features that entered the score. Cost is intentionally absent."""
    used: list[str] = []
    for name in score_features:
        for feature_name in _RAW_FEATURES.get(name, (name,)):
            if feature_name not in used:
                used.append(feature_name)
    if "schedule_similarity" in score_features and temporal_precision == "day":
        for feature_name in ("overlap_days", "schedule_overlap_months"):
            if feature_name not in used:
                used.append(feature_name)
    if "schedule_similarity" in score_features and temporal_precision == "year":
        if "overlap_years" not in used:
            used.append("overlap_years")
    return used

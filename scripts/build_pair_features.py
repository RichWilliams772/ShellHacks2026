# Aaron Green
# Adds geographic and temporal features to every Duke x TECO pair from Task 2.

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.geographic import calculate_endpoint_proximity  # noqa: E402
from analysis.temporal import calculate_temporal_features  # noqa: E402

PAIRS_CSV = ROOT / "data" / "processed" / "duke_teco_candidate_pairs.csv"
OUT_CSV = ROOT / "data" / "processed" / "duke_teco_pair_features.csv"

GEOGRAPHIC_FIELDS = [
    "geography_available", "geography_point_count_a", "geography_point_count_b",
    "minimum_endpoint_distance_miles", "project_a_nearest_endpoint",
    "project_b_nearest_endpoint", "pair_geography_confidence", "geographic_score",
    "geographic_reason",
]
TEMPORAL_FIELDS = [
    "temporal_data_available", "temporal_precision", "schedule_overlap",
    "schedule_overlap_months", "same_active_year", "year_difference",
    "temporal_score", "temporal_reason",
]


def project_a_view(row):
    return {
        "from_lat": row["project_a_from_lat"], "from_lon": row["project_a_from_lon"],
        "to_lat": row["project_a_to_lat"], "to_lon": row["project_a_to_lon"],
        "location_confidence": row["project_a_location_confidence"],
        "start": row["project_a_start"], "end": row["project_a_end"],
        "in_service_year": row["project_a_in_service_year"],
        "date_precision": row["project_a_date_precision"],
    }


def project_b_view(row):
    return {
        "from_lat": row["project_b_from_lat"], "from_lon": row["project_b_from_lon"],
        "to_lat": row["project_b_to_lat"], "to_lon": row["project_b_to_lon"],
        "location_confidence": row["project_b_location_confidence"],
        "start": row["project_b_start"], "end": row["project_b_end"],
        "in_service_year": row["project_b_in_service_year"],
        "date_precision": row["project_b_date_precision"],
    }


def build_features(pairs):
    rows = []
    for row in pairs.to_dict("records"):
        project_a, project_b = project_a_view(row), project_b_view(row)
        features = {**row,
                   **calculate_endpoint_proximity(project_a, project_b),
                   **calculate_temporal_features(project_a, project_b)}
        rows.append(features)
    return rows


def summarize(rows, original_field_order):
    total = len(rows)
    geo_available = [r for r in rows if r["geography_available"]]
    full_geo = [r for r in geo_available
               if r["geography_point_count_a"] == 2 and r["geography_point_count_b"] == 2]
    partial_geo = [r for r in geo_available if r not in full_geo]
    no_geo = [r for r in rows if not r["geography_available"]]

    distances = sorted(r["minimum_endpoint_distance_miles"] for r in geo_available)

    temporal_available = [r for r in rows if r["temporal_data_available"]]
    by_precision = {}
    for row in rows:
        by_precision.setdefault(row["temporal_precision"], []).append(row)
    overlapping = [r for r in rows if r["schedule_overlap"] is True]
    zero_overlap = [r for r in rows if r["schedule_overlap"] is False]

    print("=" * 70)
    print("TASK 3 VALIDATION REPORT")
    print("=" * 70)
    print(f"total candidate pairs:              {total}")
    print(f"pairs with geographic data:          {len(geo_available)}")
    print(f"pairs without geographic data:        {len(no_geo)}")
    print(f"  full geography (2 pts each side):  {len(full_geo)}")
    print(f"  partial geography:                 {len(partial_geo)}")
    if distances:
        n = len(distances)
        median = distances[n // 2] if n % 2 else (distances[n // 2 - 1] + distances[n // 2]) / 2
        print(f"  min endpoint distance (mi):        {distances[0]:.2f}")
        print(f"  median endpoint distance (mi):     {median:.2f}")
        print(f"  max endpoint distance (mi):        {distances[-1]:.2f}")
    print(f"null geographic scores:              {sum(1 for r in rows if r['geographic_score'] is None)}")
    print()
    print(f"pairs with temporal data:            {len(temporal_available)}")
    for precision in ("month", "year", "mixed", "unknown"):
        print(f"  precision = {precision:<8}             {len(by_precision.get(precision, []))}")
    print(f"pairs with known schedule overlap:   {len(overlapping)}")
    print(f"pairs with calculated zero overlap:  {len(zero_overlap)}")
    print(f"null temporal scores:                {sum(1 for r in rows if r['temporal_score'] is None)}")
    print("=" * 70)


def print_sanity_checks(rows):
    print("\nSANITY CHECK - closest geographic pairs (not a ranking):")
    closest = sorted((r for r in rows if r["geography_available"]),
                     key=lambda r: r["minimum_endpoint_distance_miles"])[:8]
    for row in closest:
        print(f"  {row['pair_id']:<32} {row['minimum_endpoint_distance_miles']:>6.1f} mi  "
              f"({row['project_a_nearest_endpoint']}/{row['project_b_nearest_endpoint']}, "
              f"{row['pair_geography_confidence']})  "
              f"{row['project_a_name'][:28]:<28} <-> {row['project_b_name'][:28]}")

    print("\nSANITY CHECK - temporal examples:")

    def first_matching(predicate, label):
        match = next((r for r in rows if predicate(r)), None)
        if match:
            print(f"  [{label}] {match['pair_id']}: {match['temporal_reason']} "
                  f"(precision={match['temporal_precision']}, score={match['temporal_score']})")
        else:
            print(f"  [{label}] none found in this dataset")

    first_matching(lambda r: r["temporal_precision"] == "month" and r["schedule_overlap"],
                   "month-level overlap")
    first_matching(lambda r: r["temporal_precision"] in ("year", "mixed") and r["same_active_year"],
                   "same-year / mixed compatibility")
    first_matching(lambda r: r["temporal_precision"] in ("year", "mixed") and not r["same_active_year"],
                   "year apart, no overlap claimed")
    first_matching(lambda r: r["temporal_precision"] == "unknown", "missing temporal data")


def main():
    pairs = pd.read_csv(PAIRS_CSV)
    original_field_order = list(pairs.columns)

    rows = build_features(pairs)
    fields = original_field_order + GEOGRAPHIC_FIELDS + TEMPORAL_FIELDS

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {len(rows)} pairs with features to {OUT_CSV.relative_to(ROOT)}\n")
    summarize(rows, original_field_order)
    print_sanity_checks(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
